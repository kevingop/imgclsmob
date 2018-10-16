import logging
import os
import multiprocessing
import numpy as np
import cv2

import tensorflow as tf
from tensorpack.models import regularize_cost
from tensorpack.tfutils.summary import add_moving_summary
from tensorpack import ModelDesc
from tensorpack import InputDesc, PlaceholderInput, TowerContext
from tensorpack.tfutils import get_model_loader, model_utils
from tensorpack.dataflow import imgaug, dataset, AugmentImageComponent, PrefetchDataZMQ, MultiThreadMapData, BatchData
from tensorpack.utils import logger

from .model_provider import get_model


class ImageNetModel(ModelDesc):

    def __init__(self,
                 model_lambda,
                 **kwargs):
        super(ImageNetModel, self).__init__(**kwargs)
        self.model_lambda = model_lambda
        self.image_shape = 224

        """
        uint8 instead of float32 is used as input type to reduce copy overhead.
        It might hurt the performance a liiiitle bit.
        The pretrained models were trained with float32.
        """
        self.image_dtype = tf.uint8

        """
        Either 'NCHW' or 'NHWC'
        """
        self.data_format = 'NCHW'

        """
        Whether the image is BGR or RGB. If using DataFlow, then it should be BGR.
        """
        self.image_bgr = True

        self.weight_decay = 1e-4

        """
        To apply on normalization parameters, use '.*/W|.*/gamma|.*/beta'
        """
        self.weight_decay_pattern = '.*/W'

        """
        Scale the loss, for whatever reasons (e.g., gradient averaging, fp16 training, etc)
        """
        self.loss_scale = 1.0

        """
        Label smoothing (See tf.losses.softmax_cross_entropy)
        """
        self.label_smoothing = 0.0

    def inputs(self):
        return [tf.placeholder(self.image_dtype, [None, self.image_shape, self.image_shape, 3], 'input'),
                tf.placeholder(tf.int32, [None], 'label')]

    def build_graph(self,
                    image,
                    label):

        image = self.image_preprocess(image)
        assert self.data_format in ['NCHW', 'NHWC']
        if self.data_format == 'NCHW':
            image = tf.transpose(image, [0, 3, 1, 2])

        logits = self.get_logits(image)
        loss = ImageNetModel.compute_loss_and_error(
            logits, label, label_smoothing=self.label_smoothing)

        if self.weight_decay > 0:
            wd_loss = regularize_cost(self.weight_decay_pattern,
                                      tf.contrib.layers.l2_regularizer(self.weight_decay),
                                      name='l2_regularize_loss')
            add_moving_summary(loss, wd_loss)
            total_cost = tf.add_n([loss, wd_loss], name='cost')
        else:
            total_cost = tf.identity(loss, name='cost')
            add_moving_summary(total_cost)

        if self.loss_scale != 1.:
            logger.info("Scaling the total loss by {} ...".format(self.loss_scale))
            return total_cost * self.loss_scale
        else:
            return total_cost

    def get_logits(self,
                   image):
        """
        Args:
            image: 4D tensor of ``self.input_shape`` in ``self.data_format``

        Returns:
            Nx#class logits
        """
        return self.model_lambda(image)

    def optimizer(self):
        lr = tf.get_variable('learning_rate', initializer=0.1, trainable=False)
        tf.summary.scalar('learning_rate-summary', lr)
        return tf.train.MomentumOptimizer(lr, 0.9, use_nesterov=True)

    def image_preprocess(self,
                         image):

        with tf.name_scope('image_preprocess'):
            if image.dtype.base_dtype != tf.float32:
                image = tf.cast(image, tf.float32)
            mean = [0.485, 0.456, 0.406]    # rgb
            std = [0.229, 0.224, 0.225]
            if self.image_bgr:
                mean = mean[::-1]
                std = std[::-1]
            image_mean = tf.constant(mean, dtype=tf.float32) * 255.
            image_std = tf.constant(std, dtype=tf.float32) * 255.
            image = (image - image_mean) / image_std
            return image

    @staticmethod
    def compute_loss_and_error(logits,
                               label,
                               label_smoothing=0.0):

        if label_smoothing == 0.0:
            loss = tf.nn.sparse_softmax_cross_entropy_with_logits(logits=logits, labels=label)
        else:
            nclass = logits.shape[-1]
            loss = tf.losses.softmax_cross_entropy(
                tf.one_hot(label, nclass),
                logits, label_smoothing=label_smoothing)
        loss = tf.reduce_mean(loss, name='xentropy-loss')

        def prediction_incorrect(logits, label, topk=1, name='incorrect_vector'):
            with tf.name_scope('prediction_incorrect'):
                x = tf.logical_not(tf.nn.in_top_k(logits, label, topk))
            return tf.cast(x, tf.float32, name=name)

        wrong = prediction_incorrect(logits, label, 1, name='wrong-top1')
        add_moving_summary(tf.reduce_mean(wrong, name='train-error-top1'))

        wrong = prediction_incorrect(logits, label, 5, name='wrong-top5')
        add_moving_summary(tf.reduce_mean(wrong, name='train-error-top5'))
        return loss


class GoogleNetResize(imgaug.ImageAugmentor):
    """
    crop 8%~100% of the original image
    See `Going Deeper with Convolutions` by Google.
    """
    def __init__(self, crop_area_fraction=0.08,
                 aspect_ratio_low=0.75, aspect_ratio_high=1.333,
                 target_shape=224):
        self._init(locals())

    def _augment(self, img, _):
        h, w = img.shape[:2]
        area = h * w
        for _ in range(10):
            targetArea = self.rng.uniform(self.crop_area_fraction, 1.0) * area
            aspectR = self.rng.uniform(self.aspect_ratio_low, self.aspect_ratio_high)
            ww = int(np.sqrt(targetArea * aspectR) + 0.5)
            hh = int(np.sqrt(targetArea / aspectR) + 0.5)
            if self.rng.uniform() < 0.5:
                ww, hh = hh, ww
            if hh <= h and ww <= w:
                x1 = 0 if w == ww else self.rng.randint(0, w - ww)
                y1 = 0 if h == hh else self.rng.randint(0, h - hh)
                out = img[y1:y1 + hh, x1:x1 + ww]
                out = cv2.resize(out, (self.target_shape, self.target_shape), interpolation=cv2.INTER_CUBIC)
                return out
        out = imgaug.ResizeShortestEdge(self.target_shape, interp=cv2.INTER_CUBIC).augment(img)
        out = imgaug.CenterCrop(self.target_shape).augment(out)
        return out


def get_imagenet_dataflow(datadir,
                          is_train,
                          batch_size,
                          augmentors,
                          parallel=None):
    """
    See explanations in the tutorial:
    http://tensorpack.readthedocs.io/en/latest/tutorial/efficient-dataflow.html
    """
    assert datadir is not None
    assert isinstance(augmentors, list)
    if parallel is None:
        parallel = min(40, multiprocessing.cpu_count() // 2)  # assuming hyperthreading
    if is_train:
        ds = dataset.ILSVRC12(datadir, 'train', shuffle=True)
        ds = AugmentImageComponent(ds, augmentors, copy=False)
        if parallel < 16:
            logging.warning("DataFlow may become the bottleneck when too few processes are used.")
        ds = PrefetchDataZMQ(ds, parallel)
        ds = BatchData(ds, batch_size, remainder=False)
    else:
        ds = dataset.ILSVRC12Files(datadir, 'val', shuffle=False)
        aug = imgaug.AugmentorList(augmentors)

        def mapf(dp):
            fname, cls = dp
            im = cv2.imread(fname, cv2.IMREAD_COLOR)
            im = aug.augment(im)
            return im, cls
        ds = MultiThreadMapData(ds, parallel, mapf, buffer_size=2000, strict=True)
        ds = BatchData(ds, batch_size, remainder=True)
        ds = PrefetchDataZMQ(ds, 1)
    return ds


def prepare_tf_context(num_gpus,
                       batch_size):
    batch_size *= max(1, num_gpus)
    return batch_size


def prepare_model(model_name,
                  classes,
                  use_pretrained,
                  pretrained_model_file_path):
    kwargs = {'pretrained': use_pretrained,
              'classes': classes}

    net = get_model(model_name, **kwargs)
    net = ImageNetModel(model_lambda=net)

    inputs_desc = None
    if pretrained_model_file_path:
        assert (os.path.isfile(pretrained_model_file_path))
        logging.info('Loading model: {}'.format(pretrained_model_file_path))
        inputs_desc = get_model_loader(pretrained_model_file_path)

    return net, inputs_desc


def get_data(is_train,
             batch_size,
             data_dir_path):

    if is_train:
        augmentors = [
            GoogleNetResize(crop_area_fraction=0.08),
            imgaug.RandomOrderAug([
                imgaug.BrightnessScale((0.6, 1.4), clip=False),
                imgaug.Contrast((0.6, 1.4), clip=False),
                imgaug.Saturation(0.4, rgb=False),
                # rgb-bgr conversion for the constants copied from fb.resnet.torch
                imgaug.Lighting(
                    0.1,
                    eigval=np.asarray([0.2175, 0.0188, 0.0045][::-1]) * 255.0,
                    eigvec=np.array([
                        [-0.5675, 0.7192, 0.4009],
                        [-0.5808, -0.0045, -0.8140],
                        [-0.5836, -0.6948, 0.4203]], dtype='float32')[::-1, ::-1])]),
            imgaug.Flip(horiz=True)]
    else:
        augmentors = [
            imgaug.ResizeShortestEdge(256, cv2.INTER_CUBIC),
            imgaug.CenterCrop((224, 224))]

    return get_imagenet_dataflow(
        datadir=data_dir_path,
        is_train=is_train,
        batch_size=batch_size,
        augmentors=augmentors)


def calc_flops(model):
    # manually build the graph with batch=1
    input_desc = [
        InputDesc(tf.float32, [1, 224, 224, 3], 'input'),
        InputDesc(tf.int32, [1], 'label')
    ]
    input = PlaceholderInput()
    input.setup(input_desc)
    with TowerContext('', is_training=False):
        model.build_graph(*input.get_input_tensors())
    model_utils.describe_trainable_vars()

    tf.profiler.profile(
        tf.get_default_graph(),
        cmd='op',
        options=tf.profiler.ProfileOptionBuilder.float_operation())
    logger.info("Note that TensorFlow counts flops in a different way from the paper.")
    logger.info("TensorFlow counts multiply+add as two flops, however the paper counts them "
                "as 1 flop because it can be executed in one instruction.")