#!/usr/bin/env python3
import numpy as np
import sys,os
import argparse

def IntersectionOverUnion(box_1, box_2):
    xmin=0
    ymin=1
    xmax=2
    ymax=3
    width_of_overlap_area  = min(box_1[xmax], box_2[xmax]) - max(box_1[xmin], box_2[xmin])
    height_of_overlap_area = min(box_1[ymax], box_2[ymax]) - max(box_1[ymin], box_2[ymin]);
    if width_of_overlap_area < 0 or height_of_overlap_area < 0:
        area_of_overlap = 0
    else:
        area_of_overlap = width_of_overlap_area * height_of_overlap_area
    box_1_area = (box_1[ymax] - box_1[ymin])  * (box_1[xmax] - box_1[xmin])
    box_2_area = (box_2[ymax] - box_2[ymin])  * (box_2[xmax] - box_2[xmin])
    area_of_union = box_1_area + box_2_area - area_of_overlap
    if area_of_union == 0: return 0.0
    return area_of_overlap / area_of_union

def read_box(filename,w=1.0,h=1.0):
    f = open(filename)
    lines = f.readlines()
    ary = []
    for l in lines:
        l = l.strip().split(' ')
        ary.append(l)
    ary = np.asarray(ary,dtype=np.float32).reshape(-1)
    ary[1::5] = w*ary[1::5]
    ary[2::5] = h*ary[2::5]
    ary[3::5] = w*ary[3::5]
    ary[4::5] = h*ary[4::5]
    ary = ary.reshape(-1,5)
    return ary

def compare_with_IOU(gt,pr,iou_thresh=0.5,verbose=False):
    assert type(gt) == np.ndarray,'arg gt must be numpy.array'
    assert type(pr) == np.ndarray,'arg pr must be numpy.array'
    if verbose:print("GroundTrush:%d Predicted:%d"%(gt.shape[0], pr.shape[0]))
    TP = []
    FP = []
    TN = []
    if verbose:print("# TP GT and iou")
    for pi in range(pr.shape[0]):
        predict_bbox = pr[pi][1:]
        matched=False
        for gi in range(gt.shape[0]):
            ground_bbox = gt[gi][1:]
            iou = IntersectionOverUnion(predict_bbox, ground_bbox)
            iou = int(10000.*iou)/10000.
            if iou > iou_thresh:
                if verbose:print(predict_bbox, ground_bbox,iou)
                TP.append(predict_bbox)
                matched=True
                gt[gi]=np.zeros((5),dtype=np.float32)
                break
        if not matched:
            FP.append(predict_bbox)
    TP = np.asarray(TP)
    FP = np.asarray(FP)
    TN = gt[gt>0.0].reshape(-1,5)
    return TP, FP, TN

def calc_precision_recall(TP,FP,TN):
    assert type(TP) == np.ndarray or type(TP) == list, "needs ndarray or list"
    assert type(FP) == np.ndarray or type(FP) == list, "needs ndarray or list"
    assert type(TN) == np.ndarray or type(TN) == list, "needs ndarray or list"
    nTP=len(TP)
    nFP=len(FP)
    nTN=len(TN)
    precision = nTP/(nTP+nFP)
    recall    = nTP/(nTP+nTN)
    print("# TP FP TN Precision Recall")
    print("%d %d %d %.4f %.4f"%(nTP,nFP,nTN,precision,recall))
    return precision, recall

if __name__ == '__main__':
    args = argparse.ArgumentParser('calcurate precision etc.')
    args.add_argument("-g", "--gt", type=str, nargs='+', help="Ground Truth files")
    args.add_argument("-p", "--pr", type=str, nargs='+', help="Prediction result files")
    args.add_argument("-i", "--iou",type=float, default=0.5, help="IOU Threshold")
    args.add_argument("-v", "--verbose",action='store_true', help="Verbose for debug")
    args = args.parse_args()
    assert len(args.gt)==len(args.pr), 'mismatched number of files'

    iou_thresh = args.iou

    for gt_file,pr_file in zip(args.gt, args.pr):
        gt_bbox=read_box(gt_file,w=1.0,h=1.0)
        pr_bbox=read_box(pr_file,w=640,h=480)

        tp, fp, tn = compare_with_IOU(gt_bbox,pr_bbox,iou_thresh,args.verbose)
        calc_precision_recall(tp,fp,tn)

