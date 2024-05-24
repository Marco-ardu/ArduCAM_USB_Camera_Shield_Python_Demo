import sys
from pathlib import Path

import ArducamSDK
import arducam_config_parser
import time

import cv2
from PIL import ImageDraw, ImageFont, Image
import numpy as np
from loguru import logger


usb_config = """
;**************************************************************************************/
; ----- camera parameter -----
; [camera parameter]	Camera parameter set for USB2.0 & USB3.0 mode
;
; -- Keyname description:
; CFG_MODE  = set the config mode for camera: 0 -> User define(UI)
;											  1 -> This config File
; TYPE      = set the name of the camera module
; SIZE		= set the width and height of the image generated by camera 
; BIT_WIDTH = set the bit width of the image generated by camera 
; FORMAT    = set the format of the image generated by camera:
;				| 0 -> RAW	  | 1 -> RGB565  | 2 -> YUV422   | 3 -> JPG  | 4 -> MONO  | 5 -> ST_RAW	| 6 -> ST_MONO |  
;				| -- 0 -> RG  | -- 0 -> RGB  | -- 0 -> YUYV  |           | 			  | -- 0 -> RG  | 			   |  
;				| -- 1 -> GR  | -- 1 -> BGR  | -- 1 -> YVYU  |           | 			  | -- 1 -> GR  | 			   |  
;				| -- 2 -> GB  |              | -- 2 -> UYVY  |           |			  | -- 2 -> GB  |			   |  
;				| -- 3 -> BG  |              | -- 3 -> VYUY  |           | 			  | -- 3 -> BG  | 			   |  
; I2C_MODE  = set the bit width of the address and data of I2C communication: 
;				0 ->  8 bit address &  8 bit value				
;				1 ->  8 bit address & 16 bit value
;				2 -> 16 bit address &  8 bit value
;				3 -> 16 bit address & 16 bit value		
; I2C_ADDR  = set the I2C address for register config of camera 
; G_GAIN    = set the address for green1_gain register config of camera	( RAW & RGB565 & ST_RAW mode )
; B_GAIN    = set the address for blue_gain register config of camera	( RAW & RGB565 & ST_RAW mode )
; R_GAIN    = set the address for red_gain register config of camera	( RAW & RGB565 & ST_RAW mode )
; G2_GAIN   = set the address for green2_gain register config of camera	( RAW & ST_RAW mode )
; Y_GAIN    = set the address for Y_gain register config of camera		( YUV422 mode )
; U_GAIN    = set the address for U_gain register config of camera		( YUV422 mode )
; V_GAIN    = set the address for V_gain register config of camera		( YUV422 mode )
; GL_GAIN   = set the address for global_gain register config of camera
; 
; -- Keyname format:
; CFG_MODE  = <value1>							;<comment>
; TYPE      = <value1>
; SIZE		= <width>, <height>
; BIT_WIDTH = <bitWidth>
; FORMAT    = <value1>[, <value2>]
; I2C_MODE  = <value1>
; I2C_ADDR  = <i2cAddress> 
; G_GAIN    = [<page>,] <address>, <minValue>, <maxValue>
; B_GAIN    = [<page>,] <address>, <minValue>, <maxValue>
; R_GAIN    = [<page>,] <address>, <minValue>, <maxValue>
; G2_GAIN   = [<page>,] <address>, <minValue>, <maxValue>
; Y_GAIN    = [<page>,] <address>, <minValue>, <maxValue>
; U_GAIN    = [<page>,] <address>, <minValue>, <maxValue>
; V_GAIN    = [<page>,] <address>, <minValue>, <maxValue>
; GL_GAIN   = [<page>,] <address>, <minValue>, <maxValue>
; 
; <valueN>		Index value representing certain meanings 
; <width>		Width of the image generated by camera
; <height>		Height of the image generated by camera
; <bitWidth>	Bit width of the image generated by camera
; <i2cAddress>	I2C address for register config of camera
; <page>        Optional address space for this register. Some sensors (mostly SOC's)
;               have multiple register pages (see the sensor spec or developers guide)
; <address>     The register address 
; <minValue>	Minimale value of certain address
; <maxValue>	Maximale value of certain address
; <comment>    	Some form of C-style comments are supported in this .cfg file
;
;**************************************************************************************/
[camera parameter]
CFG_MODE  = 0	
TYPE      = IMX377
SIZE      = 4104, 3046 
BIT_WIDTH = 8 
FORMAT    = 0, 3
I2C_MODE  = 2					
I2C_ADDR  = 0x34
;TRANS_LVL = 128

[control parameter]
MIN_VALUE   = 0
MAX_VALUE   = 32767
STEP        = 1
DEF 		= 0
CTRL_NAME	= Focus
FUNC_NAME	= setFocus
======CODE_BLOCK_START======
function setFocus(val)
    data = {0, 0}
    start_cmd = {0xFE, 0x80}
    end_cmd = {0x0d}
	val = math.floor(val) | 0x8000
	high = (val & 0xFF00) >> 8
	low = (val & 0x00FF)

	ret = SendVR(0xD5, 0xE400, 0x1600, 2, start_cmd)


    data[1] = high
    data[2] = low
    ret = SendVR(0xD5, 0xE400, 0xA100, 2, data)

	ret = SendVR(0xD7, 0xE400, 0x8A00, 1, end_cmd)

end
======CODE_BLOCK_END======


;**************************************************************************************/
; ----- board parameter -----
;
; -- Keyname description:
; VRCMD = set board parameter by vendor command 
; 
; -- Keyname format:
; VRCMD = <command>, <value>, <index>, <dataNumber>[, <data1>[, <data2>[, <data3>[, <data4>]]]] 		//<comment>
;
; <command>     
; <value>      
; <index>         
; <dataNumber>  
; <dataN>      
; <comment>    Some form of C-style comments are supported in this .cfg file
;
;**************************************************************************************/
[board parameter]
VRCMD = 0xD7, 0x4600, 0x0100, 1, 0x4D
VRCMD = 0xD7, 0x4600, 0x0200, 1, 0x00
VRCMD = 0xD7, 0x4600, 0x0300, 1, 0xC0
VRCMD = 0xD7, 0x4600, 0x0300, 1, 0x40
VRCMD = 0xD7, 0x4600, 0x0400, 1, 0x15
VRCMD = 0xD7, 0x4600, 0x0A00, 1, 0x01
VRCMD = 0xD7, 0x4600, 0x0C00, 1, 0xA2
VRCMD = 0xD7, 0x4600, 0x0D00, 1, 0x0f
VRCMD = 0xD7, 0x4600, 0x0E00, 1, 0xb8
VRCMD = 0xD7, 0x4600, 0x0F00, 1, 0x0b
VRCMD = 0xD7, 0x4600, 0x1000, 1, 0xe6
VRCMD = 0xD7, 0x4600, 0x1100, 1, 0x03
VRCMD = 0xD7, 0x4600, 0x2300, 1, 0x01
VRCMD = 0xF6, 0x0000, 0x0000, 3, 0x03, 0x04, 0x0C
VRCMD = 0xD7, 0x4600, 0x2900, 1, 0x01   //camera B

// INIT Focus 
VRCMD = 0xD7, 0xE400, 0x8000, 1, 0x34 
VRCMD = 0xD7, 0xE400, 0x8100, 1, 0x20 
VRCMD = 0xD7, 0xE400, 0x8400, 1, 0xE0 
VRCMD = 0xD7, 0xE400, 0x8700, 1, 0x05 
VRCMD = 0xD7, 0xE400, 0xA400, 1, 0x24 
VRCMD = 0xD7, 0xE400, 0x3A00, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x3B00, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x0400, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x0500, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x0200, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x0300, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x1800, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x1900, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x4000, 1, 0x80 
VRCMD = 0xD7, 0xE400, 0x4100, 1, 0x10 
VRCMD = 0xD7, 0xE400, 0x4200, 1, 0x75 
VRCMD = 0xD7, 0xE400, 0x4300, 1, 0x70 
VRCMD = 0xD7, 0xE400, 0x4400, 1, 0x8B 
VRCMD = 0xD7, 0xE400, 0x4500, 1, 0x50 
VRCMD = 0xD7, 0xE400, 0x4600, 1, 0x6A 
VRCMD = 0xD7, 0xE400, 0x4700, 1, 0x10 
VRCMD = 0xD7, 0xE400, 0x4800, 1, 0x5A 
VRCMD = 0xD7, 0xE400, 0x4900, 1, 0x90 
VRCMD = 0xD7, 0xE400, 0x4A00, 1, 0x20 
VRCMD = 0xD7, 0xE400, 0x4B00, 1, 0x30 
VRCMD = 0xD7, 0xE400, 0x4C00, 1, 0x32 
VRCMD = 0xD7, 0xE400, 0x4D00, 1, 0xF0 
VRCMD = 0xD7, 0xE400, 0x4E00, 1, 0x80 
VRCMD = 0xD7, 0xE400, 0x4F00, 1, 0x10 
VRCMD = 0xD7, 0xE400, 0x5000, 1, 0x04 
VRCMD = 0xD7, 0xE400, 0x5100, 1, 0xF0 
VRCMD = 0xD7, 0xE400, 0x5200, 1, 0x76 
VRCMD = 0xD7, 0xE400, 0x5300, 1, 0x10 
VRCMD = 0xD7, 0xE400, 0x5400, 1, 0x14 
VRCMD = 0xD7, 0xE400, 0x5500, 1, 0x50 
VRCMD = 0xD7, 0xE400, 0x5600, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x5700, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x5800, 1, 0x7F 
VRCMD = 0xD7, 0xE400, 0x5900, 1, 0xF0 
VRCMD = 0xD7, 0xE400, 0x5A00, 1, 0x08 
VRCMD = 0xD7, 0xE400, 0x5B00, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x5C00, 1, 0x72 
VRCMD = 0xD7, 0xE400, 0x5D00, 1, 0xF0 
VRCMD = 0xD7, 0xE400, 0x5E00, 1, 0x7F 
VRCMD = 0xD7, 0xE400, 0x5F00, 1, 0x70 
VRCMD = 0xD7, 0xE400, 0x6000, 1, 0x7E 
VRCMD = 0xD7, 0xE400, 0x6100, 1, 0xD0 
VRCMD = 0xD7, 0xE400, 0x6200, 1, 0x7F 
VRCMD = 0xD7, 0xE400, 0x6300, 1, 0xF0 
VRCMD = 0xD7, 0xE400, 0x6400, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x6500, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x6600, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x6700, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x6800, 1, 0x51 
VRCMD = 0xD7, 0xE400, 0x6900, 1, 0x30 
VRCMD = 0xD7, 0xE400, 0x6A00, 1, 0x72 
VRCMD = 0xD7, 0xE400, 0x6B00, 1, 0xF0 
VRCMD = 0xD7, 0xE400, 0x6C00, 1, 0x80 
VRCMD = 0xD7, 0xE400, 0x6D00, 1, 0x10 
VRCMD = 0xD7, 0xE400, 0x6E00, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x6F00, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x7000, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x7100, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x7200, 1, 0x18 
VRCMD = 0xD7, 0xE400, 0x7300, 1, 0xE0 
VRCMD = 0xD7, 0xE400, 0x7400, 1, 0x4E 
VRCMD = 0xD7, 0xE400, 0x7500, 1, 0x30 
VRCMD = 0xD7, 0xE400, 0x3000, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x3100, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x7600, 1, 0x0C 
VRCMD = 0xD7, 0xE400, 0x7700, 1, 0x50 
VRCMD = 0xD7, 0xE400, 0x7800, 1, 0x20 
VRCMD = 0xD7, 0xE400, 0x7900, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x8600, 1, 0x60 
VRCMD = 0xD7, 0xE400, 0x8800, 1, 0x6C 
VRCMD = 0xD7, 0xE400, 0x2800, 1, 0x81 
VRCMD = 0xD7, 0xE400, 0x2900, 1, 0x8F 
VRCMD = 0xD7, 0xE400, 0x4C00, 1, 0x32 
VRCMD = 0xD7, 0xE400, 0x4D00, 1, 0xF0 
VRCMD = 0xD7, 0xE400, 0x8300, 1, 0xAC 
VRCMD = 0xD7, 0xE400, 0x8500, 1, 0xC0 
VRCMD = 0xD7, 0xE400, 0x8400, 1, 0xE3 
VRCMD = 0xD7, 0xE400, 0x9700, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x9800, 1, 0x42 
VRCMD = 0xD7, 0xE400, 0x9900, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x9A00, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0x9300, 1, 0x40 
VRCMD = 0xD7, 0xE400, 0x7C00, 1, 0x01 
VRCMD = 0xD7, 0xE400, 0x7D00, 1, 0x80 
VRCMD = 0xD7, 0xE400, 0xA000, 1, 0x00 
VRCMD = 0xD7, 0xE400, 0xA100, 1, 0x02 
VRCMD = 0xD7, 0xE400, 0x8700, 1, 0x85 
                     
//Focus adjust
//START					 
VRCMD = 0xD7, 0xE400, 0x1600, 1, 0xFE 
VRCMD = 0xD7, 0xE400, 0x1700, 1, 0x80

//SET Focus
VRCMD = 0xD7, 0xE400, 0xA100, 1, 0x80 
VRCMD = 0xD7, 0xE400, 0xA200, 1, 0x00 

//END	
VRCMD = 0xD7, 0xE400, 0x8A00, 1, 0x0D



[board parameter][dev2]


[board parameter][dev3][inf2]
VRCMD = 0xD7, 0x4600, 0x0300, 1, 0x00
VRCMD = 0xD7, 0x4600, 0x0400, 1, 0x00
VRCMD = 0xF3, 0x0000, 0x0000, 0
VRCMD = 0xF9, 0x0004, 0x0000, 0

[board parameter][dev3][inf3]
VRCMD = 0xD7, 0x4600, 0x0300, 1, 0x00
VRCMD = 0xD7, 0x4600, 0x0400, 1, 0x00
VRCMD = 0xF3, 0x0000, 0x0000, 0
VRCMD = 0xF9, 0x0004, 0x0000, 0

;**************************************************************************************/
; ----- register parameter -----
;
; -- Keyname description:
; REG    = assign a new register value
; DELAY  = delay a certain amount of milliseconds before continuing
; BITSET = do a set operation to part of a register. The part is defined as a mask.
; BITCLR = do a reset operation to part of a register. The part is defined as a mask.
;
; -- Keyname format:
; REG    = [<page>,] <address>, <value>             //<comment>
; DELAY  = <milliseconds>
; BITSET = [<page>,] <address>, <mask>
; BITCLR = [<page>,] <address>, <mask>
;
; <page>         Optional address space for this register. Some sensors (mostly SOC's)
;                have multiple register pages (see the sensor spec or developers guide)
; <address>      the register address
; <value>        the new value to assign to the register
; <mask>         is the part of a register value that needs to be updated with a new value
; <milliseconds> wait for this ammount of milliseconds before continuing 
; <comment>      Some form of C-style comments are supported in this .cfg file
;
;**************************************************************************************/
[register parameter]
REG = 0x0103 , 0x01
DELAY = 100
REG = 0x3120, 0xf0
REG = 0x3121, 0x00
REG = 0x3122, 0x02
REG = 0x3123, 0x01
REG = 0x3124, 0x00
REG = 0x3125, 0x01
REG = 0x3127, 0x02
REG = 0x3129, 0x90
REG = 0x312a, 0x02
REG = 0x312d, 0x02
REG = 0x3003, 0x20
REG = 0x3045, 0x32
REG = 0x304e, 0x02
REG = 0x3057, 0x4a
REG = 0x3058, 0xf6
REG = 0x3059, 0x00
REG = 0x306b, 0x04
REG = 0x3145, 0x00
REG = 0x3202, 0x63
REG = 0x3203, 0x00
REG = 0x3236, 0x64
REG = 0x3237, 0x00
REG = 0x3304, 0x0b
REG = 0x3305, 0x00
REG = 0x3306, 0x0b
REG = 0x3307, 0x00
REG = 0x337f, 0x64
REG = 0x3380, 0x00
REG = 0x338d, 0x64
REG = 0x338e, 0x00
REG = 0x3510, 0x72
REG = 0x3511, 0x00
REG = 0x3528, 0x0f
REG = 0x3529, 0x0f
REG = 0x352a, 0x0f
REG = 0x352b, 0x0f
REG = 0x3538, 0x0f
REG = 0x3539, 0x13
REG = 0x353c, 0x01
REG = 0x3553, 0x00
REG = 0x3554, 0x00
REG = 0x3555, 0x00
REG = 0x3556, 0x00
REG = 0x3557, 0x00
REG = 0x3558, 0x00
REG = 0x3559, 0x00
REG = 0x355a, 0x00
REG = 0x357d, 0x07
REG = 0x357f, 0x07
REG = 0x3580, 0x04
REG = 0x3583, 0x60
REG = 0x3587, 0x01
REG = 0x3590, 0x0b
REG = 0x3591, 0x00
REG = 0x35ba, 0x0f

REG = 0x366a, 0x0c

REG = 0x366b, 0x0b
REG = 0x366c, 0x07
REG = 0x366d, 0x00
REG = 0x366e, 0x00
REG = 0x366f, 0x00
REG = 0x3670, 0x00
REG = 0x3671, 0x00
REG = 0x3672, 0x00
REG = 0x3673, 0x00
REG = 0x3674, 0xdf
REG = 0x3675, 0x00
REG = 0x3676, 0xa7
REG = 0x3677, 0x01
REG = 0x3687, 0x00
REG = 0x375c, 0x02
REG = 0x3799, 0x00
REG = 0x380a, 0x0a
REG = 0x382b, 0x16
REG = 0x3ac4, 0x01
REG = 0x303d, 0x02
REG = 0x3000, 0x16
REG = 0x3018, 0xa2
REG = 0x3399, 0x01
REG = 0x310b, 0x11
REG = 0x3a56, 0x00
REG = 0x310b, 0x00
REG = 0x3000, 0x04
REG = 0x3004, 0x00
REG = 0x3005, 0x07
REG = 0x3006, 0x00
REG = 0x3007, 0xa0  
REG = 0x3008, 0x00
REG = 0x3009, 0x00
REG = 0x300a, 0x00
REG = 0x3011, 0x00
REG = 0x302d, 0x00
REG = 0x300b, 0xce
REG = 0x300c, 0x0a
REG = 0x300d, 0x02  //0x00
REG = 0x300e, 0x00
REG = 0x301a, 0x00
REG = 0x3039, 0x00
REG = 0x303a, 0x00
REG = 0x303e, 0x00
REG = 0x303f, 0x00
REG = 0x3040, 0x00
REG = 0x3068, 0x00
REG = 0x307e, 0x00
REG = 0x307f, 0x00
REG = 0x3080, 0x00
REG = 0x3081, 0x00
REG = 0x3082, 0x00
REG = 0x3083, 0x00
REG = 0x3084, 0x00
REG = 0x3085, 0x00
REG = 0x3086, 0x00
REG = 0x3087, 0x00
REG = 0x3095, 0x00
REG = 0x3096, 0x00
REG = 0x3097, 0x00
REG = 0x3098, 0x00
REG = 0x3099, 0x00
REG = 0x309a, 0x00
REG = 0x309b, 0x00
REG = 0x309c, 0x00
REG = 0x30bc, 0x00
REG = 0x30bd, 0x00
REG = 0x30be, 0x00
REG = 0x30bf, 0x00
REG = 0x30c0, 0x00
REG = 0x30c1, 0x00
REG = 0x30c2, 0x00
REG = 0x30c3, 0x00
REG = 0x30c4, 0x00
REG = 0x30c5, 0x00
REG = 0x30c6, 0x00
REG = 0x30c7, 0x00
REG = 0x30c8, 0x00
REG = 0x30c9, 0x00
REG = 0x30ca, 0x00
REG = 0x30cb, 0x00
REG = 0x30cc, 0x00
REG = 0x30d0, 0x00
REG = 0x30d1, 0x00
REG = 0x30d5, 0x00
REG = 0x30d6, 0x00
REG = 0x30d7, 0x00
REG = 0x30d8, 0x00
REG = 0x30d9, 0x00
REG = 0x30da, 0x00
REG = 0x30ee, 0x01
REG = 0x30f5, 0x28
REG = 0x30f6, 0x05
REG = 0x30f7, 0x4e
REG = 0x30f8, 0x0c
REG = 0x30f9, 0x00
REG = 0x312f, 0xf6
REG = 0x3130, 0x0b
REG = 0x3131, 0xe6
REG = 0x3132, 0x0b
REG = 0x3a41, 0x10
REG = 0x3133, 0x77
REG = 0x3134, 0x00
REG = 0x3137, 0x37
REG = 0x3138, 0x00
REG = 0x3135, 0x67
REG = 0x3136, 0x00
REG = 0x313b, 0x37
REG = 0x313c, 0x00
REG = 0x3139, 0x37
REG = 0x313a, 0x00
REG = 0x313f, 0x37
REG = 0x3140, 0x00
REG = 0x313d, 0xdf
REG = 0x313e, 0x00
REG = 0x3141, 0x2f
REG = 0x3142, 0x00
REG = 0x3a86, 0x47
REG = 0x3a87, 0x00
REG = 0x3143, 0x0f
REG = 0x3144, 0x00
REG = 0x3001, 0x10
REG = 0x30f4, 0x00
REG = 0x3a3b, 0x00
REG = 0x3a43, 0x00
REG = 0x3a54, 0x08
REG = 0x3a55, 0x10
REG = 0x0100, 0x01
REG = 0x5040, 0x00



[register parameter][dev3][inf2]


[register parameter][dev3][inf3]



"""


ErrorCode_Map = {
    0x0000: "USB_CAMERA_NO_ERROR",
    0xFF01: "USB_CAMERA_USB_CREATE_ERROR",
    0xFF02: "USB_CAMERA_USB_SET_CONTEXT_ERROR",
    0xFF03: "USB_CAMERA_VR_COMMAND_ERROR",
    0xFF04: "USB_CAMERA_USB_VERSION_ERROR",
    0xFF05: "USB_CAMERA_BUFFER_ERROR",
    0xFF06: "USB_CAMERA_NOT_FOUND_DEVICE_ERROR",
    0xFF0B: "USB_CAMERA_I2C_BIT_ERROR",
    0xFF0C: "USB_CAMERA_I2C_NACK_ERROR",
    0xFF0D: "USB_CAMERA_I2C_TIMEOUT",
    0xFF20: "USB_CAMERA_USB_TASK_ERROR",
    0xFF21: "USB_CAMERA_DATA_OVERFLOW_ERROR",
    0xFF22: "USB_CAMERA_DATA_LACK_ERROR",
    0xFF23: "USB_CAMERA_FIFO_FULL_ERROR",
    0xFF24: "USB_CAMERA_DATA_LEN_ERROR",
    0xFF25: "USB_CAMERA_FRAME_INDEX_ERROR",
    0xFF26: "USB_CAMERA_USB_TIMEOUT_ERROR",
    0xFF30: "USB_CAMERA_READ_EMPTY_ERROR",
    0xFF31: "USB_CAMERA_DEL_EMPTY_ERROR",
    0xFF51: "USB_CAMERA_SIZE_EXCEED_ERROR",
    0xFF61: "USB_USERDATA_ADDR_ERROR",
    0xFF62: "USB_USERDATA_LEN_ERROR",
    0xFF71: "USB_BOARD_FW_VERSION_NOT_SUPPORT_ERROR"
}


def setPath():
    logPath = ''
    if getattr(sys, 'frozen', False):
        dirname = Path(sys.executable).resolve().parent
        logPath = dirname / 'logs.txt'
    elif __file__:
        logPath = Path("./logs.txt")
    logger.add(logPath.as_posix(), rotation='10 MB')


setPath()


@logger.catch
def GetErrorString(ErrorCode):
    return ErrorCode_Map[ErrorCode]


@logger.catch
def configBoard(handle, config):
    ArducamSDK.Py_ArduCam_setboardConfig(handle, config.params[0],
                                         config.params[1], config.params[2], config.params[3],
                                         config.params[4:config.params_length])


@logger.catch
def camera_initFromFile(fileName, index):
    # load config file
    config = arducam_config_parser.LoadConfigFile(fileName)

    camera_parameter = config.camera_param.getdict()
    width = camera_parameter["WIDTH"]
    height = camera_parameter["HEIGHT"]

    BitWidth = camera_parameter["BIT_WIDTH"]
    ByteLength = 1
    if BitWidth > 8 and BitWidth <= 16:
        ByteLength = 2
    FmtMode = camera_parameter["FORMAT"][0]
    color_mode = camera_parameter["FORMAT"][1]
    logger.info("color mode: {}".format(color_mode))

    I2CMode = camera_parameter["I2C_MODE"]
    I2cAddr = camera_parameter["I2C_ADDR"]
    TransLvl = camera_parameter["TRANS_LVL"]
    cfg = {"u32CameraType": 0x00,
           "u32Width": width, "u32Height": height,
           "usbType": 0,
           "u8PixelBytes": ByteLength,
           "u16Vid": 0,
           "u32Size": 0,
           "u8PixelBits": BitWidth,
           "u32I2cAddr": I2cAddr,
           "emI2cMode": I2CMode,
           "emImageFmtMode": FmtMode,
           "u32TransLvl": TransLvl}

    ret, handle, rtn_cfg = ArducamSDK.Py_ArduCam_open(cfg, index)
    # ret, handle, rtn_cfg = ArducamSDK.Py_ArduCam_autoopen(cfg)
    if ret == 0:

        # ArducamSDK.Py_ArduCam_writeReg_8_8(handle,0x46,3,0x00)
        usb_version = rtn_cfg['usbType']
        configs = config.configs
        configs_length = config.configs_length
        for i in range(configs_length):
            type = configs[i].type
            if ((type >> 16) & 0xFF) != 0 and ((type >> 16) & 0xFF) != usb_version:
                continue
            if type & 0xFFFF == arducam_config_parser.CONFIG_TYPE_REG:
                # print(" 0x{:04X}, 0x{:02X}".format(configs[i].params[0], configs[i].params[1]))
                ArducamSDK.Py_ArduCam_writeSensorReg(
                    handle, configs[i].params[0], configs[i].params[1])
            elif type & 0xFFFF == arducam_config_parser.CONFIG_TYPE_DELAY:
                time.sleep(float(configs[i].params[0]) / 1000)
            elif type & 0xFFFF == arducam_config_parser.CONFIG_TYPE_VRCMD:
                configBoard(handle, configs[i])

        ArducamSDK.Py_ArduCam_registerCtrls(
            handle, config.controls, config.controls_length)

        rtn_val, datas = ArducamSDK.Py_ArduCam_readUserData(
            handle, 0x400 - 16, 16)
        logger.info("Serial: %c%c%c%c-%c%c%c%c-%c%c%c%c" % (datas[0], datas[1], datas[2], datas[3],
                                                      datas[4], datas[5], datas[6], datas[7],
                                                      datas[8], datas[9], datas[10], datas[11]))

        return True, handle, rtn_cfg, color_mode

    logger.info("open fail, Error : {}".format(GetErrorString(ret)))
    return False, handle, rtn_cfg, color_mode


@logger.catch
def camera_initCPLD(fileName, index):
    # load config file
    config = arducam_config_parser.LoadConfigFile(fileName)

    camera_parameter = config.camera_param.getdict()
    width = camera_parameter["WIDTH"]
    height = camera_parameter["HEIGHT"]

    BitWidth = camera_parameter["BIT_WIDTH"]
    ByteLength = 1
    if 8 < BitWidth <= 16:
        ByteLength = 2
    FmtMode = camera_parameter["FORMAT"][0]
    color_mode = camera_parameter["FORMAT"][1]
    logger.info("color mode: {}".format(color_mode))

    I2CMode = camera_parameter["I2C_MODE"]
    I2cAddr = camera_parameter["I2C_ADDR"]
    TransLvl = camera_parameter["TRANS_LVL"]
    cfg = {"u32CameraType": 0x00,
           "u32Width": width, "u32Height": height,
           "usbType": 0,
           "u8PixelBytes": ByteLength,
           "u16Vid": 0,
           "u32Size": 0,
           "u8PixelBits": BitWidth,
           "u32I2cAddr": I2cAddr,
           "emI2cMode": I2CMode,
           "emImageFmtMode": FmtMode,
           "u32TransLvl": TransLvl}

    ret, handle, rtn_cfg = ArducamSDK.Py_ArduCam_open(cfg, index)
    # ret, handle, rtn_cfg = ArducamSDK.Py_ArduCam_autoopen(cfg)

    if ret == 0:
        configs = config.configs
        configs_length = config.configs_length
        for i in range(configs_length):
            type = configs[i].type
            if ((type >> 16) & 0xFF) != 0 and ((type >> 16) & 0xFF) != rtn_cfg['usbType']:
                continue
            if type & 0xFFFF == arducam_config_parser.CONFIG_TYPE_DELAY:
                time.sleep(float(configs[i].params[0]) / 1000)
            elif type & 0xFFFF == arducam_config_parser.CONFIG_TYPE_VRCMD:
                configBoard(handle, configs[i])
        return True, handle, rtn_cfg, config, I2cAddr, color_mode

    logger.error("initialize fail, Error : {}".format(GetErrorString(ret)))
    return False, handle, rtn_cfg, config, I2cAddr, color_mode


@logger.catch
def camera_initSensor(handle, readConfig, usb_version, I2cAddr):
    # ArducamSDK.Py_ArduCam_writeReg_8_8(handle,0x46,3,0x00)
    # usb_version = rtn_cfg['usbType']
    configs = readConfig.configs
    configs_length = readConfig.configs_length
    for i in range(configs_length):
        type = configs[i].type
        if ((type >> 16) & 0xFF) != 0 and ((type >> 16) & 0xFF) != usb_version:
            continue
        if type & 0xFFFF == arducam_config_parser.CONFIG_TYPE_REG:
            # print(f" {configs[i].params[0]}, {configs[i].params[1]}")
            ArducamSDK.Py_ArduCam_writeSensorReg(
                handle, configs[i].params[0], configs[i].params[1])
        elif type & 0xFFFF == arducam_config_parser.CONFIG_TYPE_DELAY:
            time.sleep(float(configs[i].params[0]) / 1000)
        # elif type & 0xFFFF == arducam_config_parser.CONFIG_TYPE_VRCMD:
        #     configBoard(handle, configs[i])

    ArducamSDK.Py_ArduCam_registerCtrls(
        handle, readConfig.controls, readConfig.controls_length)

    rtn_val, datas = ArducamSDK.Py_ArduCam_readUserData(
        handle, 0x400 - 16, 16)
    logger.info("Serial: %c%c%c%c-%c%c%c%c-%c%c%c%c" % (datas[0], datas[1], datas[2], datas[3],
                                                  datas[4], datas[5], datas[6], datas[7],
                                                  datas[8], datas[9], datas[10], datas[11]))


@logger.catch
def DetectI2c(camera):
    ret = 0
    value_hi = 0
    value_lo = 0
    if camera is not None:
        # ret, value = ArducamSDK.Py_ArduCam_readSensorReg(camera.handle, 0x0F12)
        # logger.info("0x{:02x}".format(value))
        ret, value = ArducamSDK.Py_ArduCam_readReg_8_8(camera.handle, camera.I2cAddr, 0x00)
        # ret, value_hi = ArducamSDK.Py_ArduCam_readSensorReg(camera.handle, 0x0000)
        # logger.info(f"ret: {ret}, value_H: {value_hi:02X}")
        # ret, value_lo = ArducamSDK.Py_ArduCam_readSensorReg(camera.handle, 0x0001)
        # logger.info(f"ret: {ret}, value_L: {value_lo:02X}")
    # return value_hi == 0x01 and value_lo == 0xB0
    logger.info("ret: {}, i2c addr: 0x{:02X}".format(ret, camera.I2cAddr))
    return not ret


@logger.catch
def cv2AddChineseText(img, text, position, textColor=(0, 255, 0), textSize=30):
    if isinstance(img, np.ndarray):
        img = Image.fromarray(cv2.cvtColor(img, cv2.COLOR_BGR2RGB))
    draw = ImageDraw.Draw(img)
    fontStyle = ImageFont.truetype("font/simsun.ttc", textSize, encoding="utf-8")
    draw.text(position, text, textColor, font=fontStyle)
    return cv2.cvtColor(np.asarray(img), cv2.COLOR_RGB2BGR)
