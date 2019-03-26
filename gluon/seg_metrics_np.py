"""
Routines for segmentation metrics on numpy.
"""

import numpy as np

__all__ = ['seg_pixel_accuracy_np', 'segm_mean_accuracy_hmasks', 'segm_mean_accuracy', 'seg_mean_iou_np',
           'segm_mean_iou2', 'seg_mean_iou_imasks_np', 'segm_fw_iou_hmasks', 'segm_fw_iou']


def seg_pixel_accuracy_np(label_imask,
                          pred_imask,
                          vague_idx=-1,
                          use_vague=False):
    """
    The segmentation pixel accuracy.

    Parameters
    ----------
    label_imask : np.array
        Ground truth index mask (maybe batch of).
    pred_imask : np.array
        Predicted index mask (maybe batch of).
    vague_idx : int, default -1
        Index of masked pixels.
    use_vague : bool, default False
        Whether to use pixel masking.

    Returns
    -------
    float
        PA metric value.
    """
    assert (label_imask.shape == pred_imask.shape)
    if use_vague:
        sum_u_ij = np.sum(label_imask.flat != vague_idx)
        if sum_u_ij == 0:
            return 0.0
        sum_u_ii = np.sum(np.logical_and(pred_imask.flat == label_imask.flat, label_imask.flat != vague_idx))
    else:
        sum_u_ii = np.sum(pred_imask.flat == label_imask.flat)
        sum_u_ij = pred_imask.size
    return float(sum_u_ii) / sum_u_ij


def segm_mean_accuracy_hmasks(label_hmask,
                              pred_hmask):
    """
    The segmentation mean accuracy.

    Parameters
    ----------
    label_hmask : np.array
        Ground truth one-hot mask.
    pred_hmask : np.array
        Predicted one-hot mask.

    Returns
    -------
    float
        MA metric value.
    """
    assert (pred_hmask.shape == label_hmask.shape)
    assert (len(pred_hmask.shape) == 3)
    n = label_hmask.shape[0]
    i_sum = 0
    acc_sum = 0.0
    for i in range(n):
        class_i_pred_mask = pred_hmask[i, :, :]
        class_i_label_mask = label_hmask[i, :, :]

        u_i = np.sum(class_i_label_mask)
        if u_i == 0:
            continue

        u_ii = np.sum(np.logical_and(class_i_pred_mask, class_i_label_mask))

        class_acc = float(u_ii) / u_i
        acc_sum += class_acc
        i_sum += 1

    if i_sum > 0:
        mean_acc = acc_sum / i_sum
    else:
        mean_acc = 1.0

    return mean_acc


def segm_mean_accuracy(label_hmask,
                       pred_imask):
    """
    The segmentation mean accuracy.

    Parameters
    ----------
    label_hmask : np.array
        Ground truth one-hot mask.
    pred_imask : np.array
        Predicted index mask.

    Returns
    -------
    float
        MA metric value.
    """
    assert (len(label_hmask.shape) == 3)
    assert (len(pred_imask.shape) == 2)
    assert (pred_imask.shape == label_hmask.shape[1:])
    n = label_hmask.shape[0]
    i_sum = 0
    acc_sum = 0.0
    for i in range(n):
        class_i_pred_mask = (pred_imask == i)
        class_i_label_mask = label_hmask[i, :, :]

        u_i = np.sum(class_i_label_mask)
        if u_i == 0:
            continue

        u_ii = np.sum(np.logical_and(class_i_pred_mask, class_i_label_mask))

        class_acc = float(u_ii) / u_i
        acc_sum += class_acc
        i_sum += 1

    if i_sum > 0:
        mean_acc = acc_sum / i_sum
    else:
        mean_acc = 1.0

    return mean_acc


def segm_mean_iou_imasks(label_hmask,
                         pred_hmask):
    """
    The segmentation mean accuracy.

    Parameters
    ----------
    label_hmask : np.array
        Ground truth one-hot mask.
    pred_hmask : np.array
        Predicted one-hot mask.

    Returns
    -------
    float
        MA metric value.
    """
    assert (pred_hmask.shape == label_hmask.shape)
    assert (len(pred_hmask.shape) == 3)
    n = label_hmask.shape[0]
    i_sum = 0
    acc_sum = 0.0
    for i in range(n):
        class_i_pred_mask = pred_hmask[i, :, :]
        class_i_label_mask = label_hmask[i, :, :]

        u_i = np.sum(class_i_label_mask)
        if u_i == 0:
            continue

        u_ii = np.sum(np.logical_and(class_i_pred_mask, class_i_label_mask))

        class_acc = float(u_ii) / u_i
        acc_sum += class_acc
        i_sum += 1

    if i_sum > 0:
        mean_acc = acc_sum / i_sum
    else:
        mean_acc = 1.0

    return mean_acc


def seg_mean_iou_np(label_hmask,
                    pred_imask):
    """
    The segmentation mean intersection over union.

    Parameters
    ----------
    label_hmask : np.array
        Ground truth one-hot mask.
    pred_imask : np.array
        Predicted index mask.

    Returns
    -------
    float
        MIoU metric value.
    """
    assert (len(label_hmask.shape) == 3)
    assert (len(pred_imask.shape) == 2)
    assert (pred_imask.shape == label_hmask.shape[1:])
    n = label_hmask.shape[0]
    i_sum = 0
    acc_iou = 0.0
    for i in range(n):
        class_i_pred_mask = (pred_imask == i)
        class_i_label_mask = label_hmask[i, :, :]

        u_i = np.sum(class_i_label_mask)
        u_ji_sj = np.sum(class_i_pred_mask)
        if (u_i + u_ji_sj) == 0:
            continue

        u_ii = np.sum(np.logical_and(class_i_pred_mask, class_i_label_mask))

        acc_iou += float(u_ii) / (u_i + u_ji_sj - u_ii)
        i_sum += 1

    if i_sum > 0:
        mean_iou = acc_iou / i_sum
    else:
        mean_iou = 1.0

    return mean_iou


def segm_mean_iou2(label_hmask,
                   pred_hmask):
    """
    The segmentation mean intersection over union.

    Parameters
    ----------
    label_hmask : nd.array
        Ground truth one-hot mask (batch of).
    pred_hmask : nd.array
        Predicted one-hot mask (batch of).

    Returns
    -------
    float
        MIoU metric value.
    """
    assert (len(label_hmask.shape) == 4)
    assert (len(pred_hmask.shape) == 4)
    assert (pred_hmask.shape == label_hmask.shape)

    eps = np.finfo(np.float32).eps
    class_axis = 1  # The axis that represents classes

    inter_hmask = label_hmask * pred_hmask
    u_i = label_hmask.sum(axis=[2, 3])
    u_ji_sj = pred_hmask.sum(axis=[2, 3])
    u_ii = inter_hmask.sum(axis=[2, 3])
    class_count = (u_i + u_ji_sj > 0.0).sum(axis=class_axis) + eps
    class_acc = u_ii / (u_i + u_ji_sj - u_ii + eps)
    acc_iou = class_acc.sum(axis=class_axis) + eps
    mean_iou = (acc_iou / class_count).mean().asscalar()

    return mean_iou


def seg_mean_iou_imasks_np(label_imask,
                           pred_imask,
                           num_classes,
                           ignore_bg=False):
    """
    The segmentation mean intersection over union.

    Parameters
    ----------
    label_imask : nd.array
        Ground truth index mask (batch of).
    pred_imask : nd.array
        Predicted index mask (batch of).
    num_classes : int
        Number of classes.
    ignore_bg : bool
        Ignoring class 0, if true.

    Returns
    -------
    float
        MIoU metric value.
    """
    assert (len(label_imask.shape) == 2)
    assert (len(pred_imask.shape) == 2)
    assert (pred_imask.shape == label_imask.shape)

    eps = np.finfo(np.float32).eps

    mini = 1
    maxi = num_classes
    nbins = num_classes
    if ignore_bg:
        maxi -= 1
        nbins -= 1
        pred_imask = pred_imask * (label_imask > 0).astype(pred_imask.dtype)
    else:
        label_imask += 1
        pred_imask += 1
        if (label_imask < 0).any():
            pred_imask = pred_imask * (label_imask >= 0).astype(pred_imask.dtype)

    intersection = pred_imask * (pred_imask == label_imask)

    area_inter, _ = np.histogram(intersection, bins=nbins, range=(mini, maxi))
    area_pred, _ = np.histogram(pred_imask, bins=nbins, range=(mini, maxi))
    area_label, _ = np.histogram(label_imask, bins=nbins, range=(mini, maxi))
    area_union = area_pred + area_label - area_inter + eps

    mean_iou = (area_inter / area_union).mean()

    return mean_iou


def segm_fw_iou_hmasks(label_hmask,
                       pred_hmask):
    """
    The segmentation frequency weighted intersection over union.

    Parameters
    ----------
    label_hmask : np.array
        Ground truth one-hot mask.
    pred_hmask : np.array
        Predicted one-hot mask.

    Returns
    -------
    float
        FrIoU metric value.
    """
    assert (pred_hmask.shape == label_hmask.shape)
    assert (len(pred_hmask.shape) == 3)
    n = label_hmask.shape[0]
    acc_iou = 0.0
    for i in range(n):
        class_i_pred_mask = pred_hmask[i, :, :]
        class_i_label_mask = label_hmask[i, :, :]

        u_i = np.sum(class_i_label_mask)
        u_ji_sj = np.sum(class_i_pred_mask)
        if (u_i + u_ji_sj) == 0:
            continue

        u_ii = np.sum(np.logical_and(class_i_pred_mask, class_i_label_mask))

        acc_iou += float(u_i * u_ii) / (u_i + u_ji_sj - u_ii)

    fw_factor = pred_hmask[0].size

    return acc_iou / fw_factor


def segm_fw_iou(label_hmask,
                pred_imask):
    """
    The segmentation frequency weighted intersection over union.

    Parameters
    ----------
    label_hmask : np.array
        Ground truth one-hot mask.
    pred_imask : np.array
        Predicted index mask.

    Returns
    -------
    float
        FrIoU metric value.
    """
    assert (len(label_hmask.shape) == 3)
    assert (len(pred_imask.shape) == 2)
    assert (pred_imask.shape == label_hmask.shape[1:])
    n = label_hmask.shape[0]
    acc_iou = 0.0
    for i in range(n):
        class_i_pred_mask = (pred_imask == i)
        class_i_label_mask = label_hmask[i, :, :]

        u_i = np.sum(class_i_label_mask)
        u_ji_sj = np.sum(class_i_pred_mask)
        if (u_i + u_ji_sj) == 0:
            continue

        u_ii = np.sum(np.logical_and(class_i_pred_mask, class_i_label_mask))

        acc_iou += float(u_i * u_ii) / (u_i + u_ji_sj - u_ii)

    fw_factor = pred_imask.size

    return acc_iou / fw_factor