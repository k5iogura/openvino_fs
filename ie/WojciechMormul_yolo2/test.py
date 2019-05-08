import argparse
import os,sys
import tensorflow as tf
import numpy as np
import cv2

prob_th = 0.7
iou_th = 0.5
n_anchors = 5
n_classes = 20
n_single_out = n_anchors + n_classes
net_scale = 32
grid_w, grid_h = 18, 10
input_w, input_h = grid_w*net_scale, grid_h*net_scale
anchors_w, anchors_h = 960, 540

def read_anchors_file(file_path):

    anchors = []
    with open(file_path, 'r') as file:
    	for line in file.read().splitlines():
    		anchors.append(map(float,line.split()))

    return np.array(anchors)

def read_labels(filepath):
    
    classes, names, colors = [], [], []
    with open(filepath,'r') as file:
    	lines = file.read().splitlines()
    	for line in lines:
    		cls, name, color = line.split()
    		classes.append(int(cls))
    		names.append(name)
    		colors.append(eval(color))

    return classes, names, colors

def iou(r1,r2):
    
    intersect_w = np.maximum(np.minimum(r1[0]+r1[2],r2[0]+r2[2])-np.maximum(r1[0],r2[0]),0)
    intersect_h = np.maximum(np.minimum(r1[1]+r1[3],r2[1]+r2[3])-np.maximum(r1[1],r2[1]),0)
    area_r1 = r1[2]*r1[3]
    area_r2 = r2[2]*r2[3]
    intersect = intersect_w*intersect_h	
    union = area_r1 + area_r2 - intersect
    
    return intersect/union

def softmax(x):
    
    e_x = np.exp(x)
    return e_x/np.sum(e_x)

def sigmoid(x):
    
    return 1.0/(1.0 + np.exp(-x))

def preprocess_data(data, anchors, a_w, a_h, important_classes):
    
    locations = []
    classes = []
    for i in range(grid_h):
    	for j in range(grid_w):
    		for k in range(n_anchors):
    			
    			class_vec = softmax(data[0, i, j, k, 5:])
    			objectness = sigmoid(data[0, i, j, k, 4])
    			class_prob = objectness*class_vec
    			
    			scale_w = input_w/float(a_w)
    			scale_h = input_h/float(a_h)
    			
    			w = np.exp(data[0, i, j, k, 2])*anchors[k][0]*scale_w
    			h = np.exp(data[0, i, j, k, 3])*anchors[k][1]*scale_h
    			dx = sigmoid(data[0, i, j, k, 0])
    			dy = sigmoid(data[0, i, j, k, 1])
    			x = (j+dx)*net_scale-w/2.0
    			y = (i+dy)*net_scale-h/2.0
    			
    			classes.append(class_prob[important_classes])
    			locations.append([x, y, w, h])
    							
    classes = np.array(classes)
    locations = np.array(locations)
    	
    return classes, locations

def non_max_supression(classes, locations):

    classes = np.transpose(classes)
    indxs = np.argsort(-classes,axis=1)

    for i in range(classes.shape[0]):
    	classes[i] = classes[i][indxs[i]]

    for class_idx, class_vec in enumerate(classes):
    	for roi_idx, roi_prob in enumerate(class_vec):
    		if roi_prob < prob_th:
    			classes[class_idx][roi_idx]=0
    
    for class_idx,class_vec in enumerate(classes):
    	for roi_idx, roi_prob in enumerate(class_vec):
    		
    		if roi_prob == 0:
    			continue
    		roi = locations[indxs[class_idx][roi_idx]]
    		
    		for roi_ref_idx, roi_ref_prob in enumerate(class_vec):
    			
    			if roi_ref_prob == 0 or roi_ref_idx <= roi_idx:
    				continue

    			roi_ref = locations[indxs[class_idx][roi_ref_idx]]
    				
    			if iou(roi, roi_ref) > iou_th:
    				classes[class_idx][roi_ref_idx] = 0
    	
    return classes, indxs

def draw(classes,rois, indxs, img, names, colors):

    scale_w = img.shape[1]/float(input_w)
    scale_h = img.shape[0]/float(input_h)

    for class_idx, c in enumerate(classes):
    	for loc_idx, class_prob in enumerate(c):
    		
    		if class_prob > 0:
    			
    			x = int(rois[indxs[class_idx][loc_idx]][0]*scale_w)
    			y = int(rois[indxs[class_idx][loc_idx]][1]*scale_h)
    			w = int(rois[indxs[class_idx][loc_idx]][2]*scale_w)
    			h = int(rois[indxs[class_idx][loc_idx]][3]*scale_h)	

    			cv2.rectangle(img, (x, y), (x+w, y+h), colors[class_idx], 4)					
    			font = cv2.FONT_HERSHEY_SIMPLEX
    			text = names[class_idx] + ' %.2f'%class_prob
    			cv2.putText(img, text, (x, y-8), font, 0.7, colors[class_idx], 2)
    			print names[class_idx],class_prob

# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------
# ---------------------------------------------------------------------------

def uvc(device):

    important_classes, names, colors = read_labels('./yolo.labels')
    anchors = read_anchors_file('anchors.txt')

    sess = tf.Session() 
    saver = tf.train.import_meta_graph('./model/yolo-1000.meta')
    saver.restore(sess,'./model/yolo-1000')

    graph = tf.get_default_graph()
    image = graph.get_tensor_by_name("image_placeholder:0")
    train_flag = graph.get_tensor_by_name("flag_placeholder:0")
    y = graph.get_tensor_by_name("net/y:0")

    cap = cv2.VideoCapture(device)

    while(cap.isOpened()):

    	ret, img = cap.read()
    	if ret is not True:
    		break

    	img_for_net = cv2.resize(img,(input_w,input_h))
    	img_for_net = img_for_net/255.0
    	data = sess.run(y, feed_dict = {image: [img_for_net], train_flag: False})

    	classes,rois = preprocess_data(data, anchors, anchors_w, anchors_h, important_classes)
    	classes,indxs = non_max_supression(classes, rois)
    	draw(classes, rois, indxs, img, names, colors)

    	cv2.imshow('img', img)
    	cv2.moveWindow('img', 0, 0)
    	key = cv2.waitKey(1)
    	if key == 27: break
    	
def picture(pic_files):

    important_classes, names, colors = read_labels('./yolo.labels')
    anchors = read_anchors_file('anchors.txt')

    sess = tf.Session() 
    saver = tf.train.import_meta_graph('./model/yolo-100000.meta')
    saver.restore(sess,'./model/yolo-100000')

    graph = tf.get_default_graph()
    image = graph.get_tensor_by_name("image_placeholder:0")
    train_flag = graph.get_tensor_by_name("flag_placeholder:0")
    y = graph.get_tensor_by_name("net/y:0")

    #cap = cv2.VideoCapture('./video.MP4')
    #cap = cv2.VideoCapture(0)

    for pic_file in pic_files:

    	img = cv2.imread(pic_file)
    	assert img is not None

    	img_for_net = cv2.resize(img,(input_w,input_h))
    	img_for_net = img_for_net/255.0
    	print img_for_net.shape
    	data = sess.run(y, feed_dict = {image: [img_for_net], train_flag: False})

    	classes,rois = preprocess_data(data, anchors, anchors_w, anchors_h, important_classes)
    	classes,indxs = non_max_supression(classes, rois)
    	draw(classes, rois, indxs, img, names, colors)

    #	cv2.imshow('img', img)
    #	cv2.moveWindow('img', 0, 0)
    #	key = cv2.waitKey(0)
    #	if key == 27: break
    	
if __name__ == "__main__":
    def chk(files):
        for f in files:
            print f
            assert os.path.exists(f) is True
        return files
    args = argparse.ArgumentParser()
    args.add_argument("-m", "--mode"   ,type=str, default="uvc", choices=['uvc','jpg'], help="")
    args.add_argument("-i", "--images" ,type=str, nargs='+', help="")
    args.add_argument("-v", "--device" ,type=int, default=0, help="")
    args = args.parse_args()
    if args.mode == 'jpg':
        picture(args.images)
    else:
        uvc(args.uvc)

