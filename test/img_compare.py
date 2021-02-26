#!/usr/bin/python
from PIL import ImageChops
from PIL import Image
import math, operator
import sys
import time
import os
#import sha
import shutil
import sys
import numpy


def rmsdiff(im1, im2):
	"Calculate the root-mean-square difference between two images"

	im1 = Image.open(im1)
	im2 = Image.open(im2)
	h = ImageChops.difference(im1, im2).histogram()
	# measure the difference between the images
	# discard the top 5% of the changed areas
	return numpy.percentile(map(int,h),98)
		
if __name__ == '__main__':

	files = []
	current_slide_frame = 0
	sequential_changes = 0
	previous_diff = 0.0
	variation_level = 0
	slides_selected = False

	while True:
		time.sleep(1)

		new_files = os.listdir('/mnt/ramdisk')
		if new_files == files:
			# no new frames available yet
			continue
		
		slide_frames = []
		video_frames = []
		for f in new_files:
			try:
				frame_num = int(f[15:-4])
				if f[:15] == 'channel_2_frame':
					slide_frames.append(frame_num)
			except:
				pass
		slide_frames.sort()

		try:
			if current_slide_frame == 0:
				current_slide_frame = slide_frames[2]
		except:
			pass

		for frame in slide_frames:
			if frame <= current_slide_frame: continue

			diff = rmsdiff('/mnt/ramdisk/channel_2_frame%09d.png' % current_slide_frame,
										 '/mnt/ramdisk/channel_2_frame%09d.png' % frame )
			print str(current_slide_frame) +' vs ' + str(frame) + ' = ' +str(int(diff))

			if diff > 2000:
				# major frame-change detected
				# so grab a frame for liveslides
				shutil.copy2('/mnt/ramdisk/channel_2_frame%020d.png' % frame, '/recordings/slides/')

			current_slide_frame = frame


