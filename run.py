import math

import torch
import cv2
from time import time

from moviepy.audio.io.AudioFileClip import AudioFileClip
from moviepy.video.io.VideoFileClip import VideoFileClip

from ai_models.audio_detector import audio_utils
from event_detection.point_detection import *
from event_detection.bounce_detection import *
from event_detection.court_detection import *
from helper_functions.cv_helper import plot_boxes
import ai_models.event_detector.event as event_mod
import tensorflow as tf
import os

obj_det_model = torch.hub.load('ultralytics/yolov5', 'custom', 'ai_models/object_detection/trained/object_detect5.pt')  # custom trained model
event_det_model = event_mod.load_model('ai_models/event_detector/trained_model')

# Images

################TEST#######################################
# url = 'no_commit/test_images/frame943.jpg'  # or file, Path, URL, PIL, OpenCV, numpy, list
# results = obj_det_model (url)
# det = results.xyxy[0]
# print(det)
# img = cv2.imread(url) 
# my_img = checkIfBallInBounds(det, img)
# cv2.imshow('rect', my_img) 
# cv2.waitKey(0) # waits until a key is pressed


###REAL############
#----Detect using URL----
# play = pafy.new('https://www.youtube.com/watch?v=oyxhHkOel2I&t=1s').streams[-1]
# player = cv2.VideoCapture(play.url)
# width = int(player.get(cv2.CAP_PROP_FRAME_WIDTH))
# height = int(player.get(cv2.CAP_PROP_FRAME_HEIGHT))
# success,image = player.read()
# --------------------------------------------------------

#----Detect using downloaded video----
player = cv2.VideoCapture('no_commit/short_test.mp4')
success,image = player.read()
height, width, layers = image.shape
size = (width, height)
# ----------------------------------------------------------

out = cv2.VideoWriter('no_commit/results_fixed.avi',cv2.VideoWriter_fourcc(*"MJPG"), 20, size)
video_file = VideoFileClip('no_commit/short_test.mp4')
audio_file = video_file.audio
audio_reader = audio_file.coreader().reader
audio_reader.seek(0)
audio_model = tf.keras.models.load_model('ai_models/audio_detector/trained_model', compile=False)

prev_frame_data = []
count = 0
display_bounce = -1
display_hit = -1
while success:
  start_time = time()
  print(f"detecting frame: ${count}")

  frame_num = math.floor(count * audio_file.fps / video_file.fps)
  audio_reader.seek(frame_num)
  audio = audio_utils.get_audio(audio_reader)
  hit_detected = audio_utils.predict(audio, audio_model)[0] > 0.5
  if hit_detected:
      display_hit = 0

  det_objects = obj_det_model(image)

  # plot object detection boxes
  boxes = det_objects.xyxyn[0][:, -1].numpy(), det_objects.xyxyn[0][:, :-1].numpy()
  #objects_frame = plot_boxes(object_det_model, boxes, image)
  prev_frame_data, bounce_detected = detect_bounces(boxes, prev_frame_data, count, event_det_model)

  # doing this every frame for debug purpose
  det = det_objects.xyxy[0]
  image, boundaries = get_court_boundary(det, image, show_data=True)
  image, ball_in_bounds = checkIfBallInBounds(det, image, boundaries, show_data=True)

  if bounce_detected:
    display_bounce = 0
    #detect if ball is in bounds and draw court boundary
    det = det_objects.xyxy[0]
    #image, ball_in_bounds = checkIfBallInBounds(det, image, show_data=False)
    

  ### DEBUG ###
  if display_bounce <= 5 and display_bounce >=0:
    in_bounds = ball_in_bounds
    cv2.putText(image,'bounce', 
            (280,100), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            2,
            (255,255, 0),
            5,
            3)
    
    text = 'in bounds' if in_bounds else 'not in bounds'
    cv2.putText(image, text, 
            (550,100), 
            cv2.FONT_HERSHEY_SIMPLEX, 
            2,
            (255,255, 0),
            5,
            3)
    display_bounce += 1
  else:
    display_bounce = -1

  if (display_hit <= 5 and display_hit >=0):
      cv2.putText(image, "HIT", (550, 100), cv2.FONT_HERSHEY_SIMPLEX, 2, (255, 0, 255), 5, 3)
      display_hit += 1
  else:
      display_hit = -1


  # add frames to the output video
  out.write(image)
  #out.write(objects_frame)
  count +=1
  
  success,image = player.read()

out.release()
