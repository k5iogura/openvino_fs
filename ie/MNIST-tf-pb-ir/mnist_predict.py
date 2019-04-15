#!/usr/bin/env python3
#STEP-1
from pdb import *
import sys,os
from math import sqrt
from time import time
import cv2
import numpy as np
import argparse
from openvino.inference_engine import IENetwork, IEPlugin

import load
mnist = load.mnist

args = argparse.ArgumentParser()
args.add_argument("images", nargs='*', type=str)
args.add_argument("-d", "--device"   , type=str, default="MYRIAD", help="Default MYRIAD or CPU")
args = args.parse_args()

data_type="FP16"
if args.device == "CPU": data_type="FP32"

model_xml='./'+data_type+'/mnist.xml'
model_bin='./'+data_type+'/mnist.bin'
plugin = IEPlugin(device=args.device, plugin_dirs=None)
extension = "/inference_engine_samples/intel64/Release/lib/libcpu_extension.so"
extension = os.environ['HOME']+extension
if args.device == "CPU":plugin.add_cpu_extension(extension)
net = IENetwork(model=model_xml, weights=model_bin)	# R5

print(model_bin, "on", args.device)
exec_net = plugin.load(network=net, num_requests=1)

input_blob = next(iter(net.inputs))  #input_blob = 'data'
out_blob   = next(iter(net.outputs)) #out_blob   = 'detection_out'
print(net.inputs[input_blob].shape)
model_n, model_h_x_model_w = net.inputs[input_blob].shape #Tool kit R4
model_h = model_w = int(sqrt(model_h_x_model_w))
print("input_blob shape(from xml)", net.inputs[input_blob].shape)
print("name (input_blob : out_blob) =",input_blob,":",out_blob)

del net

Npred=40
for idx,img in enumerate(mnist.test.images):
    Npred-=1
    if Npred<0:break
    in_frame = img[np.newaxis,:]

    start = time()
    exec_net.start_async(request_id=0, inputs={input_blob: in_frame})

    if exec_net.requests[0].wait(-1) == 0:
        sec = time() - start
        res = exec_net.requests[0].outputs[out_blob]
        pred = np.argmax(res[0])
        label= np.argmax(mnist.test.labels[idx])
        est  = 'NG'
        if pred==label:est = 'Pass'
        print("predict/label = ( %d / %d ) %s"%(pred,label,est))
    else:
        print("error")

del exec_net
del plugin
sys.exit(-1)
