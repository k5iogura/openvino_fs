#!/usr/bin/env python3
#STEP-1
import sys,os
import cv2
from openvino.inference_engine import IENetwork, IEPlugin

#STEP-2
model_xml='vinosyp/models/SSD_Mobilenet/FP16/MobileNetSSD_deploy.xml'
model_bin='vinosyp/models/SSD_Mobilenet/FP16/MobileNetSSD_deploy.bin'
model_xml = os.environ['HOME'] + "/" + model_xml
model_bin = os.environ['HOME'] + "/" + model_bin
net = IENetwork(model=model_xml, weights=model_bin)

#STEP-3
plugin = IEPlugin(device='MYRIAD', plugin_dirs=None)
exec_net = plugin.load(network=net, num_requests=1)

#STEP-4
input_blob = next(iter(net.inputs))  #input_blob = 'data'
out_blob   = next(iter(net.outputs)) #out_blob   = 'detection_out'
model_n, model_c, model_h, model_w = net.inputs[input_blob].shape #Tool kit R4
print("n/c/h/w (from xml)= %d %d %d %d"%(model_n, model_c, model_h, model_w))
print("input_blob : out_blob =",input_blob,":",out_blob)

del net

#STEP-5
for f in sys.argv[1:]:
    print("input image = %s"%f)
    frame = cv2.imread(f)

    #STEP-6
    in_frame = cv2.resize(frame, (model_w, model_h))
    in_frame = in_frame.transpose((2, 0, 1))  # Change data layout from HWC to CHW
    in_frame = in_frame.reshape((model_n, model_c, model_h, model_w))

    #STEP-7
    exec_net.start_async(request_id=0, inputs={input_blob: in_frame})

    if exec_net.requests[0].wait(-1) == 0:
        res = exec_net.requests[0].outputs[out_blob]
        print(res.shape)
    else:
        print("error")

#STEP-10
del exec_net
del plugin
