print(f"Loading {__file__!r} ...")

import IPython
import bluesky.plan_stubs as bps
import matplotlib.pyplot as plt
import numpy as np
import os
import tqdm
import shutil
import sys

from scipy.optimize import curve_fit
from scipy import ndimage
from mpl_toolkits.axes_grid1 import make_axes_locatable
from datetime import datetime
from contextlib import suppress
from scipy import signal
from scipy.ndimage import gaussian_filter

#Add ctrl+c option to matplotlib
matplotlib.rcParams['toolbar'] = 'toolmanager'

warnings.simplefilter(action='ignore', category=pd.errors.PerformanceWarning)


def focusmerlin(cnttime):
    yield from bps.abs_set(merlin1.cam.acquire, 0)
    yield from bps.abs_set(merlin1.cam.acquire_time,
                           cnttime)
    yield from bps.abs_set(merlin1.cam.acquire_period,
                           cnttime)
    yield from bps.abs_set(merlin1.cam.trigger_mode,
                           0)
    yield from bps.abs_set(merlin1.cam.image_mode,
                           2)
    yield from bps.sleep(.2)
    yield from bps.abs_set(merlin1.cam.acquire, 1)


def printfig():
    plt.savefig('/home/xf03id/temp.png', bbox_inches='tight',
                pad_inches=4)
    os.system("lp -d HXN-printer-1 /home/xf03id/temp.png")


def shutter(cmd):
    # TODO get 3 button shutter setup
    target_map = {'open': shutter_open,
                  'close': shutter_close}

    target = target_map[cmd.lower()]

    yield from bps.abs_set(target, 1)
    yield from bps.sleep(5)
    yield from bps.abs_set(target, 1)
    yield from bps.sleep(5)


def mll_z_linescan(z_start, z_end, z_num,
                   mot,
                   start, end, num,
                   acq_time,
                   elem='Pt_L'):
    """
    Parameters
    ----------
    z_start, z_stop : float
        start and stop position relative to the current position

    z_num : int
        The number of z postions to measure at

    mot : {'dssx', 'dssy'}
        The string name of the motor to fly

    start, end : float
        the start and stop for the fly motor, passed to
        `fly1d`.

    num : int
        Number of positions in the fly scan,  passed to
        `fly1d`.

    acq_time : float
        Acquire time (in s(??),  passed to
        `fly1d`.

    elem : str, optional
        The element to plot.  Passed to the custom `plot` function
        defined in 60-viewer2d.py
    """
    z_step = (z_end - z_start) / z_num
    init_sz = smlld.sbz.position
    mot = {'dssx': dssx, 'dssy': dssy}[mot]

    yield from bps.movr(smlld.sbz, z_start)

    for i in range(z_num + 1):
        yield from fly1d(mot, start, end, num, acq_time)

        plot(-1, elem, 'sclr1_ch4')
        plt.title('sbz = %.3f' % smlld.sbz.position)
        yield from bps.movr(smlld.sbz, z_step)
    yield from bps.mov(smlld.sbz, init_sz)


def mll_z_fly2d(z_start, z_end, z_num, mot1, start1, end1, num1, mot2, start2, end2, num2, acq_time, elem='Au_L'):
    z_step = (z_end - z_start)/z_num
    init_sz = smlld.sbz.position
    yield from bps.movr(smlld.sbz, z_start)
    for i in range(z_num + 1):
        yield from fly2d(dets1,mot1, start1, end1, num1, mot2, start2, end2, num2, acq_time,return_speed=40)
        plot2dfly(-1, elem, 'sclr1_ch4')
        #plot_img_sum(-1)
        insertFig(note='sbz = %.3f' % smlld.sbz.position, title = ' ')
        #plt.title('sbz = %.3f' % smlld.sbz.position)
        yield from bps.movr(smlld.sbz, z_step)
        #insertFig()
    yield from bps.mov(smlld.sbz, init_sz)
    save_page()


def zp_z_2dscan(z_start, z_end, z_num, mot1, start1, end1, num1, mot2, start2, end2, num2, acq_time, elem='Co'):
    """This function hasn't been used for a while.

    TODO: convert to use 'yield from ...'.
    """
    z_step = (z_end - z_start)/z_num
    init_sz = zps.zpsz.position
    movr(zps.zpsz, z_start/1000)
    for i in range(z_num + 1):
        RE(fly2d(mot1, start1, end1, num1, mot2, start2, end2, num2, acq_time))
        plot2dfly(-1, elem, 'sclr1_ch4')
        plt.title('zpsz = %.3f' % zps.zpsz.position)
        movr(zps.zpsz, z_step/1000)
    mov(zps.zpsz, init_sz)




def sample_to_lab(xp, zp, alpha):
    x = np.cos(alpha)*xp + np.sin(alpha)*zp
    z = -np.sin(alpha)*xp + np.cos(alpha)*zp
    return(x, z)

def lab_to_sample(x, z, alpha):
    xp = np.cos(alpha)*x - np.sin(alpha)*z
    zp = np.sin(alpha)*x + np.cos(alpha)*z
    return(xp, zp)

def mll_mosaic_scan_incomplete(x_start, x_end, x_num, x_block, y_start, y_end, y_num, y_block, acq_time, elem=None):

    max_travel = 500
    angle = 15.0*np.pi/180.0

    #initialize parameters
    x_start = float(x_start)
    x_end = float(x_end)
    x_num = int(x_num)
    y_num = int(y_num)
    y_start = float(y_start)
    y_end = float(y_end)
    x_block = int(x_block)
    y_block = int(y_block)

    #read initial position
    pre_ssx = dsx.position #smll.ssx.position
    pre_ssy = dsy.position #smll.ssy.position
    pre_ssz = dsz.position #smll.ssz.position

    print('Initial dsx = ', pre_ssx)
    print('Initial dsy = ', pre_ssy)
    print('Initial dsz = ', pre_ssz)

    #calculate block size
    x_block_size = (x_end - x_start)
    y_block_size = (y_end - y_start)

    #move to first block
    dx = -(x_block*x_block_size/2.0 - 0.5*x_block_size)
    dy = -(y_block*y_block_size/2.0 - 0.5*y_block_size)

    #if np.abs(dx) < max_travel and np.abs(dy) < max_travel:
    #    #movr_sx(dx)
    #    #movr_sy(dy)
    #    #print('moving to the starting position ...')
    #    yield from bps.movr(dsx, dx)
    #    yield from bps.movr(dsy, dy)
    #    dx_start = dsx.position
    #    #print('at starting position')
    #else:
    #    raise KeyError('Too large travel range')

    #start mosaic scan
    for i in range(y_block):
        for j in range(x_block):
            #yield from smll_sync_piezos()
            yield from fly2d(dets1, dssx, x_start+0.9*(j-1)*x_block_size, x_end+0.9*(j-1)*x_block_size, x_num, dssy, y_start+0.9*i*y_block_size, y_end+0.9*i*y_block_size, y_num, acq_time, return_speed=40)
            merlin1.unstage()
            xspress3.unstage()
            yield from bps.sleep(2)
            print('sleep 2 s')
            #dx = x_block_size * 0.8
            #movr_sx(dx)
            #yield from bps.movr(dsx, dx)
            #if elem is not None:
            #    plot2dfly(-1, elem, 'sclr1_ch4')
            #    plt.close()
        #dx = -x_block_size*(x_block-1)
        #dy = y_block_size * 0.8
        #yield from bps.mov(dsx, dx_start)
        #yield from bps.movr(dsy, dy)
        #movr_sx(dx)
        #movr_sy(dy)

    #return to initial position
    #print('Return to prior positions')
    #mov_sx(pre_ssx)
    #mov_sy(pre_ssy)
    #yield from bps.mov(dsx, pre_ssx)
    #yield from bps.mov(dsy, pre_ssy)

    print('%d x %d mosaic scan finished' % (x_block, y_block))
    
def mll_mosaic_scan(x_start, x_end, x_num, x_block, y_start, y_end, y_num, y_block, acq_time, elem=None):

    max_travel = 500
    angle = 15.0*np.pi/180.0

    #initialize parameters
    x_start = float(x_start)
    x_end = float(x_end)
    x_num = int(x_num)
    y_num = int(y_num)
    y_start = float(y_start)
    y_end = float(y_end)
    x_block = int(x_block)
    y_block = int(y_block)

    #read initial position
    pre_ssx = dsx.position #smll.ssx.position
    pre_ssy = dsy.position #smll.ssy.position
    pre_ssz = dsz.position #smll.ssz.position

    print('Initial dsx = ', pre_ssx)
    print('Initial dsy = ', pre_ssy)
    print('Initial dsz = ', pre_ssz)

    #calculate block size
    x_block_size = (x_end - x_start)
    y_block_size = (y_end - y_start)

    #move to first block
    dx = -(x_block*x_block_size/2.0 - 0.5*x_block_size)
    dy = -(y_block*y_block_size/2.0 - 0.5*y_block_size)

    #if np.abs(dx) < max_travel and np.abs(dy) < max_travel:
    #    #movr_sx(dx)
    #    #movr_sy(dy)
    #    #print('moving to the starting position ...')
    #    yield from bps.movr(dsx, dx)
    #    yield from bps.movr(dsy, dy)
    #    dx_start = dsx.position
    #    #print('at starting position')
    #else:
    #    raise KeyError('Too large travel range')

    #start mosaic scan
    for i in range(y_block):
        for j in range(x_block):
            #yield from smll_sync_piezos()
            yield from fly2d(dets1, dssx, x_start+0.9*(j-1)*x_block_size, x_end+0.9*(j-1)*x_block_size, x_num, dssy, y_start+0.9*(i-1)*y_block_size, y_end+0.9*(i-1)*y_block_size, y_num, acq_time, return_speed=40)
            merlin1.unstage()
            xspress3.unstage()
            yield from bps.sleep(2)
            print('sleep 2 s')
            #dx = x_block_size * 0.8
            #movr_sx(dx)
            #yield from bps.movr(dsx, dx)
            #if elem is not None:
            #    plot2dfly(-1, elem, 'sclr1_ch4')
            #    plt.close()
        #dx = -x_block_size*(x_block-1)
        #dy = y_block_size * 0.8
        #yield from bps.mov(dsx, dx_start)
        #yield from bps.movr(dsy, dy)
        #movr_sx(dx)
        #movr_sy(dy)

    #return to initial position
    #print('Return to prior positions')
    #mov_sx(pre_ssx)
    #mov_sy(pre_ssy)
    #yield from bps.mov(dsx, pre_ssx)
    #yield from bps.mov(dsy, pre_ssy)

    print('%d x %d mosaic scan finished' % (x_block, y_block))


def mosaic_scan(x_start, x_end, x_num, y_start, y_end, y_num, dwell_time):
    x_start = float(x_start)
    x_end = float(x_end)
    x_num = int(x_num)
    y_num = int(y_num)
    y_start = float(y_start)
    y_end = float(y_end)

    # kill close-loop
    #zps.zp_kill_piezos.put(1)
    yield from bps.sleep(5)
    if x_num == 1:
        x_step = 0.0
    else:
        x_step = (x_end - x_start) / (x_num - 1)
    if y_num == 1:
        y_step = 0.0
    else:
        y_step = (y_end - y_start) / (y_num - 1)

    # read initial positions
    pre_x
    pre_yps.smary.position
    pre_ssx = zps.zpssx.position
    pre_ssy = zps.zpssy.position

    print('x_step = ', x_step)
    print('y_step = ', y_step)
    print('Original smarx = ', pre_x)
    print('Original smary = ', pre_y)
    print('Original zpssx = ', pre_ssx)
    print('Original zpssy = ', pre_ssy)

    # move to start position
    x_ini=pre_x + x_start
    y_ini = pre_y + y_start
    yield from bps.movr(smarx, x_start)
    yield from bps.movr(smary, y_start)
    x = pre_ssx + (x_start * 1000)
    y = pre_ssy + (y_start * 1000)
    yield from bps.sleep(5)


    for i in range(y_num):

        for j in range(x_num):
            print(i,zps.smary.position)
            yield ffly2d(dets_fs,zpssx, -15, 15, 40, zpssy, -15, 15, 40, dwell_time)
            merlin1.unstage()
            xspress3.unstage()
            #scan_id,df=_load_scan(-1,fill_events=False)

            current_smarx
            current_smaryps.smary.position
            '''
            plot2dfly(-1,'Zn',norm='sclr1_ch4')
            plt.title('#'+np.str(scan_id)+', smarx '+np.str(current_smarx)+', smary '+np.str(current_smary))
            printfig()
            plot2dfly(-1, 'sclr1_ch5')
            plt.title('#'+np.str(scan_id))
            printfig()
            print('scan finished, waiting for 2s...')
            '''
           # zps.zp_kill_piezos.put(1)
            yield from bps.sleep(2)
            yield from bps.movr(smarx, x_step)


        yield from bps.mov(smarx, x_ini)
        yield from bps.movr(smary, y_step)

    print('mosaic scan finished, move back to prior positions')
    yield from bps.mov(smarx, pre_x)
    yield from bps.mov(smary, pre_y)
    yield from shutter('close')


def sin_offset(x, p0, p1, p2):
    return (p0 + p1 * np.sin((x + p2) * np.pi / 180.)) / np.cos(x * np.pi / 180.)

def sin_func(x, p0, p1, p2, p3):
    return (p0 + p1 * np.sin((x + p2) *p3* np.pi / 180.))


def sin_offset_fit(x, y, para):
    para = np.array(para)
    popt, pcov = curve_fit(sin_offset, x, y, para)
    print(popt)
    y_fit = sin_offset(x, popt[0], popt[1], popt[2])
    print(x,y_fit)
    return popt, pcov, y_fit


def rot_fit(x, y):
    x = np.array(x)
    y = -1 * np.array(y)

    para = [0.1, -0.1, 0]
    #para = [4.23077509,   0.58659241,   0.21648658, -19.8329533]
    popt, pcov, y_fit = sin_offset_fit(x, y, para)

    print(popt)
    plt.figure()
    plt.plot(x, y, label='data')
    plt.plot(x, y, 'go')
    plt.plot(x, y_fit, label='fit')
    plt.legend(loc='best')
    plt.title(np.str(popt[0]) + '+' + np.str(popt[1]) +
              '*sin(x+' + np.str(popt[2]) + ')')
    plt.xlabel('x:' + np.str(-1 * popt[1] * np.sin(popt[2] * np.pi / 180.)) +
               '  z:' + np.str(-1 * popt[1] * np.cos(popt[2] * np.pi / 180.)))
    plt.show()
    return(popt)

def coarse_align_rot(x, y, pix_size):
    r0, dr, offset = rot_fit_2(x,y)
    #zps_kill_piezos()
    #mov(zps.zpsth, 0)
    dx = -dr*np.sin(offset*np.pi/180)*pix_size
    dz = -dr*np.cos(offset*np.pi/180)*pix_size
    print(dx,dz)
    #movr(zps.smarx, dx)
    #movr(zps.smarz, dz)
    #movr(smlld.dsx,dx*1000.)
    #movr(smlld.dsz,dz*1000.)


def linear_fit(x, y):
    x = np.array(x)
    y = np.array(y)

    p = np.polyfit(x, y, 1)
    y_fit = p[1] + p[0] * x
    plt.figure()
    plt.plot(x, y, 'go', label='points')
    plt.plot(x, y_fit, label='fit')
    plt.title(np.str(p[1]) + '+' + np.str(p[0]) + 'x')
    plt.show()


def inplane_angle(x, p0, p1):
    return p0 * np.sin(x * np.pi / 180) / np.sin((180 - x - p1) * np.pi / 180)


def inplane_angle_fit(x, y, para):
    para = np.array(para)
    popt, pcov = curve_fit(inplane_angle, x, y, para)
    # print(popt)
    y_fit = inplane_angle(x, popt[0], popt[1])
    return popt, pcov, y_fit


def inplane_fit(x, y):
    x = np.array(x)
    y = np.array(y)

    para = [572.7, 90]
    popt, pcov, y_fit = inplane_angle_fit(x, y, para)

    print(popt)
    plt.figure()
    plt.plot(x, y, label='data')
    plt.plot(x, y, 'go')
    plt.plot(x, y_fit, label='fit')
    plt.legend(loc='best')
    plt.title('r=' + np.str(popt[0]) + ' theta=' + np.str(popt[1]))
    plt.show()


def sin_offset_2(x, p0, p1, p2):
    return p0 + p1 * np.sin((x + p2) * np.pi / 180)


def sin_offset_fit_2(x, y, para):
    para = np.array(para)
    popt, pcov = curve_fit(sin_offset_2, x, y, para)
    # print(popt)
    y_fit = sin_offset_2(x, popt[0], popt[1], popt[2])
    return popt, pcov, y_fit


def rot_fit_2(x, y):
    x = np.array(x)
    y = np.array(y)

    para = [1, 1, -1]
    popt, pcov, y_fit = sin_offset_fit_2(x, y, para)

    print(popt)
    plt.figure()
    plt.plot(x, y, label='data')
    plt.plot(x, y, 'go')
    plt.plot(x, y_fit, label='fit')
    plt.legend(loc='best')
    plt.title(np.str(popt[0]) + '+' + np.str(popt[1]) +
              '*sin(x+' + np.str(popt[2]) + ')')
    plt.show()
    return popt[0], popt[1], popt[2]

def find_mass_center(array):
    n = np.size(array)
    tmp = 0
    for i in range(n):
        tmp += i * array[i]
    mc = np.round(tmp / np.sum(array))
    return mc

def find_mass_center_1d(array,x):
    n = np.size(array)
    tmp = 0
    for i in range(n):
        tmp += x[i] *array[i]
    mc = tmp / np.sum(array)
    return mc

def mov_to_image_center_tmp(scan_id=-1, elem='Au_L', bitflag=1, moveflag=1,piezomoveflag=1):
    df2 = db.get_table(db[scan_id],fill=False)
    xrf = np.asfarray(eval('df2.Det2_' + elem)) + np.asfarray(eval('df2.Det1_' + elem)) + np.asfarray(eval('df2.Det3_' + elem))
    hdr = db[scan_id]['start']
    x_motor = hdr['motor1']
    y_motor = hdr['motor2']
    x = np.asarray(df2[x_motor])
    y = np.asarray(df2[y_motor])
    I0 = np.asfarray(df2.sclr1_ch4)

    scan_info=db[scan_id]
    tmp = scan_info['start']
    nx=tmp['plan_args']['num1']
    ny=tmp['plan_args']['num2']

    xrf = xrf/I0
    xrf = np.asarray(np.reshape(xrf,(ny,nx)))

    if bitflag:
        xrf[xrf <= 0.2*np.max(xrf)] = 0.
        xrf[xrf > 0.2*np.max(xrf)] = 1.

    #plt.figure()
    #plt.imshow(xrf)

    b = ndimage.measurements.center_of_mass(xrf)

    iy = int(np.round(b[0]))
    ix = int(np.round(b[1]))
    i_max = ix + iy * nx

    x_cen = x[i_max]
    y_cen = y[i_max]

    #xrf_proj = np.sum(xrf,axis=1)
    #xrf_proj_d = xrf_proj - np.roll(xrf_proj,1,0)
    #i_tip = np.where(xrf_proj_d > 0.1)
    #print(i_tip[0][0])
    #y_cen = y[(i_tip[0][0])*nx]

    #plt.figure()
    #plt.plot(xrf_proj)
    #plt.plot(xrf_proj_d)

    if moveflag:
        if x_motor == 'dssx':
            if piezomoveflag:
                print('move dssx to', x_cen)
                mov(smlld.dssx,x_cen)
            else:
                print('move dsx by', x_cen)
                movr(smlld.dsx, -1.*x_cen)
            sleep(.1)

        elif x_motor == 'dssz':
            if piezomoveflag:
                print('move dssz to', x_cen)
                mov(smlld.dssz,x_cen)
            else:
                print('move dsz by', x_cen)
                movr(smlld.dsz, x_cen)
            sleep(.1)

    if moveflag:
        print('y center', y_cen)
        if piezomoveflag:
            print('move dssy to:', y_cen)
            mov(smlld.dssy,y_cen)
        else:
            #movr(smlld.dsy, y_cen*0.001)
            print('move dsy by:', y_cen*0.001)
            movr(smlld.dsy, y_cen*0.001)
    else:
        print(x_cen,y_cen)

def tomo_scan_list(angle_list, x_start, x_end, x_num,
              y_start, y_end, y_num, exposure):
    x_0 = smlld.dssx.position
    z_0 = smlld.dssz.position
    y_0 = smlld.dssy.position
    th_0 = smlld.dsth.position
    dx_0 = smlld.dsx.position
    dz_0 = smlld.dsz.position
    dy_0 = smlld.dsy.position

    angle_list = np.array(angle_list)
    angle_num = np.size(angle_list)
    x_start = float(x_start)
    x_end = float(x_end)
    x_num = int(x_num)
    y_start = float(y_start)
    y_end = float(y_end)
    y_num = int(y_num)
    exposure = float(exposure)
    offset_y = 0.32
    offset_x = 0
    #RE(fly2d(dssz, -8, 8, 80, dssy, -2, 2, 20, 0.05, return_speed=40))
    #RE(fly2d(dssz, -1, 1, 10, dssy, -1, 1, 10, 0.05, return_speed=40)) #dummy scan

    for i in range(angle_num):

        #while beamline_status.beam_current.get() <= 245:
        #    sleep(60)

        mov(smlld.dsth, angle_list[i])
        #x_start_real = x_start / np.cos(angle*np.pi/180.)
        #x_end_real = x_end / np.cos(angle*np.pi/180.)

        while (sclr2_ch4.get() < 20000):
            sleep(60)
            print('IC3 is lower than 20000, waiting...')

        if np.abs(angle_list[i]) <= 45:
            x_start_real = x_start / np.cos(angle_list[i] * np.pi / 180.)
            x_end_real = x_end / np.cos(angle_list[i] * np.pi / 180.)
            #x_range = (x_end - x_start) / np.cos(angle_list[i] * np.pi / 180.)
            #y_range = y_end - y_start
            RE(fly2d(smlld.dssx, -10, 10, 100, smlld.dssy,-2.5, 2.5, 25, 0.05, return_speed=40))
            #mov_to_image_cen_dsx(scan_id=-1, elem='Au_L', bitflag=0, moveflag=1,piezomoveflag=1)
            mov_to_image_center_tmp(scan_id=-1, elem='W_L', bitflag=1, moveflag=1,piezomoveflag=0)
            movr(smlld.dssy, offset_y)
            #RE(fly1d(smlld.dssx,-15,15,100,0.2))
            #mov_to_image_cen_corr_dsx(-1)
            #mov_to_line_center_mll(scan_id=-1,elem='Au_L',threshold=0.2,moveflag=1,movepiezoflag=1)


            sleep(1)
            RE(fly2d(smlld.dssx,x_start_real,x_end_real,x_num,smlld.dssy,
                     y_start, y_end, y_num, exposure, return_speed=40))
            #RE(fermat(smlld.dssx,smlld.dssy,x_range,y_range,0.05,1,exposure))
        else:
            x_start_real = x_start / np.abs(np.sin(angle_list[i] * np.pi / 180.))
            x_end_real = x_end / np.abs(np.sin(angle_list[i] * np.pi / 180.))
            #x_range = (x_end - x_start) / np.abs(np.sin(angle_list[i] * np.pi / 180.))
            #y_range = y_end - y_start
            RE(fly2d(smlld.dssz, -10, 10, 100, smlld.dssy,-2.5, 2.5, 25, 0.05, return_speed=40))
            #mov_to_image_cen_dsx(scan_id=-1, elem='Au_L', bitflag=0, moveflag=1,piezomoveflag=1)
            mov_to_image_center_tmp(scan_id=-1, elem='W_L', bitflag=1, moveflag=1,piezomoveflag=0)
            movr(smlld.dssy, offset_y)
            #RE(fly1d(smlld.dssz,-15,15,100,0.2))
            #mov_to_line_center_mll(scan_id=-1,elem='Au_L',threshold=0.2,moveflag=1,movepiezoflag=1)
            sleep(1)
            RE(fly2d(smlld.dssz,x_start_real,x_end_real,x_num, smlld.dssy,
                     y_start, y_end, y_num, exposure, return_speed = 40))
            #RE(fermat(smlld.dssz,smlld.dssy,x_range,y_range,0.05,1, exposure))
        #mov_to_image_cen_smar(-1)
        #mov_to_image_cen_dsx(-1)
        #merlin1.unstage()
        movr(smlld.dssy,-1*offset_y)
        print('waiting for 2 sec...')
        sleep(2)
    mov(smlld.dsth, th_0)
    mov(smlld.dssx, x_0)
    mov(smlld.dssy, y_0)
    mov(smlld.dssz, z_0)
    mov(smlld.dsx, dx_0)
    mov(smlld.dsy, dy_0)
    mov(smlld.dsz, dz_0)


def scan_translate(step_size,step_num, x_start, x_end, x_num,
              y_start, y_end, y_num, exposure):
    x_0
    z_0ps.smarz.position
    y_0 = zps.smary.position
    theta_0 = zps.zpsth.position

    step_size = float(step_size)
    step_num = int(step_num)
    x_start = float(x_start)
    x_end = float(x_end)
    x_num = int(x_num)
    y_start = float(y_start)
    y_end = float(y_end)
    y_num = int(y_num)
    exposure = float(exposure)


    for i in range(step_num):

        while (sclr2_ch4.get() < 100000):
            sleep(60)
            print('IC3 is lower than 100000, waiting...')

        RE(fly1d(zps.zpssx,-10,10,100,0.5))
        mov_to_line_center(scan_id=-1,elem='Ba',threshold=0.2,moveflag=1,movepiezoflag=0)

        RE(fly2d(zps.zpssx,x_start,x_end,x_num,zps.zpssy,
                     y_start, y_end, y_num, exposure, return_speed=40))

        movr(zps.smary,step_size/1000.)

        merlin1.unstage()
        print('waiting for 2 sec...')
        sleep(2)

    mov(zps.smarx, x_0)
    mov(zps.smary, y_0)
    mov(zps.smarz, z_0)

def tomo_scan_list_zp(angle_list, x_start, x_end, x_num,
              y_start, y_end, y_num, exposure, flag, flip_axis):
    yield from shutter('open')

    x_0
    z_0ps.smarz.position
    y_0 = zps.smary.position
    theta_0 = zps.zpsth.position

    angle_list = np.array(angle_list)
    angle_num = np.size(angle_list)
    x_start = float(x_start)
    x_end = float(x_end)
    x_num = int(x_num)
    y_start = float(y_start)
    y_end = float(y_end)
    y_num = int(y_num)
    exposure = float(exposure)

    for i in range(angle_num):
        yield from bps.mov(zps.zpsth, angle_list[i])

        while (sclr2_ch4.get() < 35000):
            yield from bps.sleep(60)
            print('IC3 is lower than 35000, waiting...')

        if np.abs(angle_list[i]) <= 45:

            x_start_real = x_start / np.abs(np.cos(angle_list[i] * np.pi / 180.))
            x_end_real = x_end / np.abs(np.cos(angle_list[i] * np.pi / 180.))
            print(x_start_real,x_end_real)
#            if angle_list[i] < -45:
#                x_start_real = (x_start+1.5) / np.cos(angle_list[i] * np.pi / 180.)
#                x_end_real = (x_end+1.5) / np.cos(angle_list[i] * np.pi / 180.)


#            RE(fly2d(zps.zpssx,-1.5,1.5,30,zps.zpssy,-1,1,20,0.1,return_speed=40))
#            mov_to_image_cen_smar(-1)

            yield from fly1d(dets1,zps.zpssx,-10,10,100,0.5)
            if flag == 'Fe':
                yield from mov_to_line_center(scan_id=-1,elem='Fe',threshold=0.1,moveflag=1,movepiezoflag=0)
            elif flag == 'Pt_M':
                yield from mov_to_line_center(scan_id=-1,elem='Pt_M',threshold=0.1,moveflag=1,movepiezoflag=0)

            #yield from fly1d(dets1,zpssy,0,10,100,0.5)
            #p1,p2 = erf_fit(-1,'zpssy','Fe')
            #plt.close()
            #plt.close()
            #yield from bps.mov(zpssy,(p1-7.3))

            if flip_axis:
                yield from fly2d(dets1,zps.zpssy,y_start,y_end,y_num,zps.zpssx,x_start_real, x_end_real, x_num, exposure, return_speed=10)
            else:
                yield from fly2d(dets1,zps.zpssx, x_start_real, x_end_real, x_num, zps.zpssy,y_start,y_end,y_num, exposure, return_speed=10)

        else:
            x_start_real = x_start / np.abs(np.sin(angle_list[i] * np.pi / 180.))
            x_end_real = x_end / np.abs(np.sin(angle_list[i] * np.pi / 180.))
            print(x_start_real,x_end_real)
#            RE(fly2d(zps.zpssz,-1.5,1.5,30,zps.zpssy,-1,1,20,0.1,return_speed=40))
#            mov_to_image_cen_smar(-1)

            yield from fly1d(dets1,zps.zpssz,-10,10,100,0.5)
            if flag == 'Fe':
                yield from mov_to_line_center(scan_id=-1,elem='Fe',threshold=0.1,moveflag=1,movepiezoflag=0)
            elif flag == 'Pt_M':
                yield from mov_to_line_center(scan_id=-1,elem='Pt_M',threshold=0.1,moveflag=1,movepiezoflag=0)

            #yield from fly1d(dets1,zpssy,0,10,100,0.5)
            #p1,p2 = erf_fit(-1,'zpssy','Fe')
            #plt.close()
            #plt.close()
            #yield from bps.mov(zpssy,(p1-7.3))

            if flip_axis:
                yield from fly2d(dets1,zps.zpssy,y_start,y_end,y_num,zps.zpssz,x_start_real, x_end_real, x_num, exposure, return_speed=10)
            else:
                yield from fly2d(dets1,zps.zpssz, x_start_real,x_end_real,x_num, zps.zpssy, y_start, y_end, y_num, exposure, return_speed=10)

        merlin1.unstage()
        print('waiting for 2 sec...')
        yield from bps.sleep(2)

    yield from shutter('close')
    yield from bps.mov(zps.zpsth, theta_0)
    yield from bps.mov(zps.smarx, x_0)
    yield from bps.mov(zps.smary, y_0)
    yield from bps.mov(zps.smarz, z_0)

def mll_tomo_scan(angle_start, angle_end, angle_num, x_start, x_end, x_num,
              y_start, y_end, y_num, exposure, elem):
    #if os.path.isfile('rotCali'):
    #    caliFile = open('rotCali','rb')
    #    y = pickle.load(caliFile)
    angle_start = float(angle_start)
    angle_end = float(angle_end)
    angle_num = int(angle_num)
    x_start = float(x_start)
    x_end = float(x_end)
    x_num = int(x_num)
    y_start = float(y_start)
    y_end = float(y_end)
    y_num = int(y_num)
    exposure = float(exposure)

    angle_step = (angle_end - angle_start) / angle_num

    fs.stage()
    yield from bps.sleep(2)
    ic_0 = sclr2_ch4.get()
    fs.unstage()

    real_th_list = []
    scanid_list = []

    th_init = smlld.dsth.position
    y_init = dssy.position

    for i in range(angle_num + 1):

        #while beamline_status.beam_current.get() <= 245:
        #    sleep(60)
        #yield from bps.mov(dssx, 0)
        #yield from bps.mov(dssz, 0)
        #yield from bps.sleep(2)
        angle = angle_start + i * angle_step
        yield from bps.mov(smlld.dsth, angle)

        y_offset1 = sin_func(angle, 0.110, -0.586, 7.85,1.96)
        y_offset2 = sin_func(th_init, 0.110, -0.586, 7.85,1.96)
        yield from bps.mov(dssy,y_init+y_offset1-y_offset2)

        while (sclr2_ch2.get() < 10000):
            yield from bps.sleep(60)
            print('IC1 is lower than 10000, waiting...')
        fs.stage()
        yield from bps.sleep(2)
        while (sclr2_ch4.get() < (0.9*ic_0)):
            yield from peak_bpm_y(-5,5,10)
            yield from peak_bpm_x(-15,15,10)
            ic_0 = sclr2_ch4.get()
        yield from bps.sleep(1)
        fs.unstage()

        #'''
        #yield from bps.mov(dssy,-2)
        if np.abs(angle) < 44.99:

            #yield from bps.mov(dssx,0)
            #yield from bps.mov(dssz,0)
            
            #used with au disk 
            #yield from fly2d(dets1,dssx,-6,6,50, dssy,-0.5,0.5,20,0.02,dead_time=0.003)
            #cx,cy = return_center_of_mass(-1,elem,0.1)
            #yield from bps.mov(dssx,cx)
            
            #'''
            yield from fly1d(dets1,dssx, -10, 10, 200, 0.03)
            xc = return_line_center(-1,elem,0.05)
            yield from bps.mov(dssx,xc)
            
            '''
            ## for CZ testing
            yield from fly1d(dets1, dssy, -3,0.25,100,0.03)  #yield from fly1d(dets1, dssy, -7,-3,100,0.03)
            yc,yw = erf_fit(-1,elem,linear_flag=False)
            plt.close()
            yc_comp = yc + 1.2 #was 5.2
            yield from bps.mov(dssy,yc_comp)

            ## another fine scan
            yield from bps.mov(dssx,0)
            yield from bps.mov(dssz,0)
            yield from fly1d(dets1,dssx, -7.5, 7.5, 100, 0.03)
            xc = return_line_center(-1,elem,0.1)
            yield from bps.mov(dssx,xc)

            #yield from fly1d(dets1,dssy,-3.5,-1.5,100,0.05)
            #edge, fwhm = erf_fit(-1,elem,'sclr1_ch4',linear_flag=False)
            #plt.close()
            #if edge + 3 < 3 and edge + 3 > 1:
            #    yield from bps.mov(dssy,edge + 3)
            #else:
            #    yield from bps.mov(dssy,2)

            '''
        else:
            #yield from bps.mov(dssx,0)
            #yield from bps.mov(dssz,0)
            
            #used with au disk
            #yield from fly2d(dets1,dssz,-6,6,50, dssy, -0.5,0.5,20,0.02,dead_time=0.003)
            #cx,cy = return_center_of_mass(-1,elem,0.1)
            #yield from bps.mov(dssz,cx)

            #'''
            #yield from bps.movr(dssy,0.3)
            #yield from bps.mov(dssz,0)
            #yield from bps.mov(dssx,0)
            yield from fly1d(dets1,dssz, -10, 10, 200, 0.03)
            xc = return_line_center(-1,elem,0.05)
            yield from bps.mov(dssz,xc)

            '''
            ## for CZ testing
            yield from fly1d(dets1, dssy, -3,0.25,100,0.03)  #yield from fly1d(dets1, dssy, -7,-3,100,0.03)
            yc,yw = erf_fit(-1,elem,linear_flag=False)
            plt.close()
            yc_comp = yc + 1.2 #was 5.2
            yield from bps.mov(dssy,yc_comp)

            #yield from bps.movr(dssy,0.3)
            yield from bps.mov(dssz,0)
            yield from bps.mov(dssx,0)
            yield from fly1d(dets1,dssz, -7.5, 7.5, 100, 0.03)
            xc = return_line_center(-1,elem,0.1)
            yield from bps.mov(dssz,xc)

            #yield from fly1d(dets1,dssy,-3.5,-1.5,100,0.05)
            #edge, fwhm = erf_fit(-1,elem,'sclr1_ch4',linear_flag=False)
            #plt.close()
            #if edge + 3 < 3 and edge + 3 > 1:
            #    yield from bps.mov(dssy,edge + 3)
            #else:
            #    yield from bps.mov(dssy,2)
            '''
        yield from fly1d(dets1, dssy, -2,2,200,0.03)
        yc = return_line_center(-1,'Au_L',0.5)
        #yc, yw = erf_fit(-1, elem, linear_flag=False)
        yield from bps.mov(dssy,yc)

        # ## for CZ testing
        # yield from fly1d(dets1, dssy, -3,0.25,100,0.03)  #yield from fly1d(dets1, dssy, -7,-3,100,0.03)
        # yc,yw = erf_fit(-1,elem,linear_flag=False)
        # plt.close()
        # yc_comp = yc + 1 #was 5.2
        # yield from bps.mov(dssy,yc_comp)

        #merlin1.unstage()
        #xspress3.unstage()

        #dy = -0.1+0.476*np.sin(np.pi*(angle*np.pi/180.0-1.26)/1.47)
        #ddy = (-0.0024*angle)-0.185
        #dy = dy+ddy
        #yield from bps.mov(dssy,y0+dy)

        #yield from fly1d(dets1,dssy, -8, 8, 160, 0.04)
        #yc = return_line_center(-1,elem,0.1)
        #yc,yw = erf_fit(-1,elem,linear_flag=False)
        #plt.close()
        #yield from bps.movr(dsy, yc)
        #yield from bps.movr(dssx,-0.5)
        #plt.close()

        #merlin1.unstage()
        #xspress3.unstage()

        #'''
    
        #yield from bps.mov(dssy,cy)

        yield from bps.sleep(1)  # This pauses seems to resolve 2D plotting issues for the scans with multiple subscans.

        if np.abs(angle) < 44.99:

            #yield from fly2d(dets1, smlld.dssz,-5,5,50,smlld.dssy,
            #         -5, 5, 50, 0.05, return_speed=40)
            #yield from mov_to_image_cen_dsx(-1)

            x_start_real = x_start / np.cos(angle * np.pi / 180.)
            x_end_real = x_end / np.cos(angle * np.pi / 180.)
            #RE(fly2d(zpssx, x_start_real, x_end_real, x_num, zpssy,
            #         y_start, y_end, y_num, exposure, return_speed=40))
            yield from fly2d(dets1, smlld.dssx,x_start_real,x_end_real,x_num,smlld.dssy,
                     y_start, y_end, y_num, exposure, return_speed=40,dead_time=0.003)

        else:
            #yield from fly2d(dets1, smlld.dssx,-5,5,50,smlld.dssy,
            #         -5, 5, 50, 0.05, return_speed=40)
            #yield from mov_to_image_cen_dsx(-1)

            x_start_real = x_start / np.abs(np.sin(angle * np.pi / 180.))
            x_end_real = x_end / np.abs(np.sin(angle * np.pi / 180.))
            #RE(fly2d(zpssz, x_start_real, x_end_real, x_num, zpssy,
            #         y_start, y_end, y_num, exposure, return_speed=40))
            yield from fly2d(dets1, smlld.dssz,x_start_real,x_end_real,x_num, smlld.dssy,
                     y_start, y_end, y_num, exposure, return_speed = 40,dead_time=0.003)

        merlin1.unstage()
        xspress3.unstage()
        #mov_to_image_cen_smar(-1)
        #yield from mov_to_image_cen_dsx(-1)
        #yield from bps.mov(dssy,cy)
        print(f"Preparing the plot of the result ...")
        yield from bps.sleep(2)
        plot2dfly(-1,elem)

        print(f"Inserting the plot into the PDF file ...")
        sid = db[-1].start['scan_id']
        yield from bps.sleep(1)
        insertFig(note = f'dsth = {dsth.position :.2f}') #title = '{}'.format(sid)
        yield from bps.sleep(1)
        plt.close()
        yield from bps.sleep(1)
        print(f"Plotting of the result is completed.")

        # h = db[-1]
        # sid = h.start['scan_id']
        # insertFig(note='dsth = {}'.format(dsth.position),title='sid={}'.format(sid))

        #merlin1.unstage()
        #xspress3.unstage()
        print('waiting for 2 sec...')
        yield from bps.sleep(2)
        '''
        h = db[-1]
        last_sid = h.start['scan_id']
        scanid_list.append(int(last_sid))
        th_pos = dsth.position
        real_th_list.append(th_pos)
        user_folder = '/data/users/2020Q2/Huang_2020Q2/'
        sid_dsth_list = np.column_stack([scanid_list,real_th_list])
        np.savetxt(os.path.join(user_folder, 'Tomo_theta_list_firstsid_{}'.format(scanid_list[0])+'.txt'),sid_dsth_list, fmt = '%5f')
        '''

    save_page()
    #yield from bps.mov(dsth, 0)



def zp_tomo_scan(angle_start, angle_end, angle_num, x_start, x_end, x_num,
              y_start, y_end, y_num, exposure, elem):
    #if os.path.isfile('rotCali'):
    #    caliFile = open('rotCali','rb')
    #    y = pickle.load(caliFile)
    angle_start = float(angle_start)
    angle_end = float(angle_end)
    angle_num = int(angle_num)
    x_start = float(x_start)
    x_end = float(x_end)
    x_num = int(x_num)
    y_start = float(y_start)
    y_end = float(y_end)
    y_num = int(y_num)
    exposure = float(exposure)
    #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
    #yield from bps.sleep(3)
    ic_0 = sclr2_ch4.get()
    #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)
    #yield from bps.sleep(3)
    angle_step = (angle_end - angle_start) / angle_num

    for i in range(angle_num + 1):
        yield from bps.mov(zpssx,0)
        yield from bps.mov(zpssy,0)
        yield from bps.mov(zpssz,0)

        angle = angle_start + i * angle_step
        yield from bps.mov(zps.zpsth, angle)

        #yield from bps.mov(zpssx,0)
        #yield from bps.mov(zpssy,0)
        #yield from bps.mov(zpssz,0)

        while (sclr2_ch2.get() < 10000):
            yield from bps.sleep(60)
            print('IC3 is lower than 1000, waiting...')
        #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
        #yield from bps.sleep(3)
        if (sclr2_ch4.get() < (0.8*ic_0)):
            yield from peak_bpm_y(-5,5,10)
            yield from peak_bpm_x(-20,20,10)
            #ic_0 = sclr2_ch4.get()
        #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)
        #yield from bps.sleep(3)


        #'''
        if np.abs(angle) <= 60.:
            #yield from bps.movr(zpssy,-1)
            yield from fly1d([fs, zebra, sclr1, xspress3], zpssx, -5, 5, 100, 0.03)
            yield from bps.sleep(1)
            xc = return_line_center(-1,elem,0.2)
            #yield from bps.movr(zpssy,1)
            #if abs(xc)<2.5:
            if not np.isnan(xc):
                yield from bps.mov(zpssx,xc)
                #yield from bps.movr(zps.smarx,xc/1000)
        else:
            #yield from bps.mov(zpssz,0)
            yield from fly1d([fs, zebra, sclr1, xspress3],zpssz, -5, 5, 100, 0.03)
            yield from bps.sleep(1)
            xc = return_line_center(-1,elem,0.2)
            #if abs(xc)<2.5:
            if not np.isnan(xc):
                yield from bps.mov(zpssz,xc)
                #yield from bps.movr(zps.smarz,xc/1000)

        #yield from bps.mov(zpssy,0)
        yield from fly1d([fs, zebra, sclr1, xspress3], zpssy, -5,5, 100, 0.03)
        yc = return_line_center(-1,elem,0.2)
        #if not np.isnan(yc):
        #    yield from bps.mov(zpssy,yc)
        #edge,fwhm = erf_fit(-1,elem)
        plt.close()
        if not np.isnan(yc):
            yield from bps.mov(zpssy,yc)
            #yield from bps.movr(zps.smary,yc/1000)
        #merlin1.unstage()
        xspress3.unstage()

        ##yield from fly1d([fs, zebra, sclr1, xspress3],zpssy, -4, 4, 80, 0.03)
        ##yield from bps.sleep(1)
        ##yc = return_line_center(-1,elem,0.2)
        #yc,yw = erf_fit(-1,elem)
        #if abs(yc)<1:
        #    yield from bps.movr(zps.smary,yc/1000)
        #yield from bps.mov(dssy,yc)
        ##if not np.isnan(yc):
        ##    yield from bps.movr(zps.smary,yc/1000)
        #'''

        '''
        if np.abs(angle) <= 45:
            yield from fly2d(dets_fs, zpssx,-8,8,60,zpssy,-6, 6, 20, 0.02, return_speed=40)
            cmx,cmy = return_center_of_mass(-1,'Ni',th=0.2)
            yield from bps.movr(smarx,cmx*0.001)
            yield from bps.movr(smary,cmy*0.001)
        else:
            yield from fly2d(dets_fs, zpssz,-8,8,60,zpssy,-6, 6, 20, 0.02, return_speed=40)
            cmx,cmy = return_center_of_mass(-1,'Ni',th=0.2)
            yield from bps.movr(smarz,cmx*0.001)
            yield from bps.movr(smary,cmy*0.001)
        '''
        merlin1.unstage()
        xspress3.unstage()


        if np.abs(angle) <= 60.0:
            # yield from fly2d(dets1,zpssx,-6.5,7,18,zpssy,-5,5.5,14,0.05,return_speed=40)
            # yield from mov_to_image_cen_dsx(-1)

            x_start_real = x_start / np.cos(angle * np.pi / 180.)
            x_end_real = x_end / np.cos(angle * np.pi / 180.)
            #yield from fly2d([fs, zebra, sclr1, xspress3], zpssy, y_start, y_end, y_num,
            #                 zpssx, x_start_real, x_end_real, x_num, exposure, return_speed=40)
            #RE(fly2d(zpssx, x_start_real, x_end_real, x_num, zpssy,
            #         y_start, y_end, y_num, exposure, return_speed=40))
            yield from fly2d(dets_fs, zps.zpssx,x_start_real, x_end_real, x_num,zps.zpssy,y_start,y_end,y_num,exposure, dead_time=0.005,return_speed=100)

        else:
            # yield from fly2d(dets1,zpssz,-6.5,7,18,zpssy,-5,5.5,14,0.05,return_speed=40)
            # yield from mov_to_image_cen_dsx(-1)

            x_start_real = x_start / np.abs(np.sin(angle * np.pi / 180.))
            x_end_real = x_end / np.abs(np.sin(angle * np.pi / 180.))
            #yield from fly2d([fs, zebra, sclr1, xspress3],zpssy, y_start, y_end, y_num,
            #                 zpssz, x_start_real, x_end_real, x_num, exposure, return_speed=40)
            #RE(fly2d(zpssz, x_start_real, x_end_real, x_num, zpssy,
            #         y_start, y_end, y_num, exposure, return_speed=40))
            yield from fly2d(dets_fs, zps.zpssz,x_start_real, x_end_real, x_num,zps.zpssy,y_start,y_end,y_num,exposure, dead_time=0.005,return_speed = 100)

        #mov_to_image_cen_smar(-1)
        #yield from mov_to_image_cen_dsx(-1)
        #plot2dfly(-1,elem,'sclr1_ch4')
        #insertFig(note='zpsth = {}'.format(check_baseline(-1,'zpsth')))
        #plt.close()
        #merlin2.unstage()
        xspress3.unstage()
        print('waiting for 2 sec...')
        #yield from bps.sleep(5)
        #if np.remainder(i+1,5)==0:
        #    yield from peak_bpm_x(-20, 20, 10)
        #    yield from peak_bpm_y(-10, 10, 10)
    save_page()

def zp_tomo_scan_scale(angle_start, angle_end, angle_num, x_start, x_end, x_num,
              y_start, y_end, y_num, exposure, elem):
    #if os.path.isfile('rotCali'):
    #    caliFile = open('rotCali','rb')
    #    y = pickle.load(caliFile)
    angle_start = float(angle_start)
    angle_end = float(angle_end)
    angle_num = int(angle_num)
    x_start = float(x_start)
    x_end = float(x_end)
    x_num = int(x_num)
    y_start = float(y_start)
    y_end = float(y_end)
    y_num = int(y_num)
    exposure = float(exposure)
    #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
    #yield from bps.sleep(3)
    ic_0 = sclr2_ch4.get()
    #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)
    #yield from bps.sleep(3)
    angle_step = (angle_end - angle_start) / angle_num

    x_offset_um = 5
    y_offset_um = 0

    for i in range(angle_num + 1):
        #yield from bps.mov(zpssx,0)
        #yield from bps.mov(zpssy,0)
        #yield from bps.mov(zpssz,0)

        angle = angle_start + i * angle_step
        yield from bps.mov(zps.zpsth, angle)


        while (sclr2_ch2.get() < 10000):
            yield from bps.sleep(60)
            print('IC3 is lower than 1000, waiting...')
        #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1)
        #yield from bps.sleep(3)
        if (sclr2_ch4.get() < (0.6*ic_0)):
            yield from peak_bpm_y(-5,5,10)
            yield from peak_bpm_x(-20,20,10)
            #ic_0 = sclr2_ch4.get()
        #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0)
        #yield from bps.sleep(3)


        #'''
        if np.abs(angle) <= 45.:

            #yield from bps.movr(zpssy,-1)
            yield from fly1d(dets_fs, zpssx, -10, 10, 100, 0.03)
            yield from bps.sleep(0.5)
            xc = return_line_center(-1,elem,0.1)
            #yield from bps.movr(zpssy,1)
            #if abs(xc)<2.5:
            if not np.isnan(xc):
                #yield from bps.mov(zpssx,xc)
                yield from bps.movr(smarx,xc/1000)
        else:
            #yield from bps.movr(smarz,5/1000)
            #yield from bps.movr(smary,5/1000)
            #yield from bps.mov(zpssz,0)
            yield from fly1d(dets_fs,zpssz, -10, 10, 100, 0.03)
            yield from bps.sleep(0.5)
            xc = return_line_center(-1,elem,0.1)
            #if abs(xc)<2.5:
            if not np.isnan(xc):
                #yield from bps.mov(zpssz,xc)
                yield from bps.movr(smarz,xc/1000)
        #'''
        #yield from bps.movr(zpssy,0)
        yield from fly1d(dets_fs, zpssy, -10,10, 100, 0.03)
        yc = return_line_center(-1,elem,0.15)
        #if not np.isnan(yc):
        #    yield from bps.mov(zpssy,yc)
        #edge,fwhm = erf_fit(-1,elem)
        plt.close()
        if not np.isnan(yc):
            yield from bps.mov(zpssy,yc)
            #yield from bps.movr(smary,(yc+y_offset_um)/1000)
        #merlin1.unstage()
        xspress3.unstage()
        #'''

        '''
        if np.abs(angle) <= 45:
            yield from fly2d(dets_fs, zpssx,-8,8,60,zpssy,-6, 6, 20, 0.02, return_speed=40)
            cmx,cmy = return_center_of_mass(-1,'Ni',th=0.2)
            yield from bps.movr(smarx,cmx*0.001)
            yield from bps.movr(smary,cmy*0.001)
        else:
            yield from fly2d(dets_fs, zpssz,-8,8,60,zpssy,-6, 6, 20, 0.02, return_speed=40)
            cmx,cmy = return_center_of_mass(-1,'Ni',th=0.2)
            yield from bps.movr(smarz,cmx*0.001)
            yield from bps.movr(smary,cmy*0.001)
        '''
        merlin1.unstage()
        xspress3.unstage()

        x_scale_factor = 0.9542
        z_scale_factor = 1.0309
        angle_offset = -2.18

        angle_tmp = angle + angle_offset
        if np.abs(angle) <= 45.0:
            # yield from fly2d(dets1,zpssx,-6.5,7,18,zpssy,-5,5.5,14,0.05,return_speed=40)
            # yield from mov_to_image_cen_dsx(-1)

            x_start_real = x_start / np.cos(angle_tmp * np.pi / 180.) / x_scale_factor
            x_end_real = x_end / np.cos(angle_tmp * np.pi / 180.) / x_scale_factor
            #yield from fly2d([fs, zebra, sclr1, xspress3], zpssy, y_start, y_end, y_num,
            #                 zpssx, x_start_real, x_end_real, x_num, exposure, return_speed=40)
            #RE(fly2d(zpssx, x_start_real, x_end_real, x_num, zpssy,
            #         y_start, y_end, y_num, exposure, return_speed=40))
            yield from fly2d(dets1, zps.zpssx,x_start_real, x_end_real, x_num,zps.zpssy,y_start,y_end,y_num,exposure, dead_time=0.005,return_speed=100)
            plot2dfly(-1,elem,'sclr1_ch4')
            insertFig(note='zpsth = {}'.format(check_baseline(-1,'zpsth')))
            plt.close()
            yield from fly2d(dets1, zps.zpssx,x_start_real, x_end_real, x_num//2,zps.zpssy,y_start,y_end,y_num//2,exposure, dead_time=0.005,return_speed=100)
            plot2dfly(-1,elem,'sclr1_ch4')
            insertFig(note='zpsth = {}'.format(check_baseline(-1,'zpsth')))
            plt.close()
            yield from fly2d(dets1, zps.zpssx,x_start_real, x_end_real, x_num//4,zps.zpssy,y_start,y_end,y_num//4,exposure, dead_time=0.005,return_speed=100)
            plot2dfly(-1,elem,'sclr1_ch4')
            insertFig(note='zpsth = {}'.format(check_baseline(-1,'zpsth')))
            plt.close()
        else:
            # yield from fly2d(dets1,zpssz,-6.5,7,18,zpssy,-5,5.5,14,0.05,return_speed=40)
            # yield from mov_to_image_cen_dsx(-1)

            x_start_real = x_start / np.abs(np.sin(angle_tmp * np.pi / 180.)) / z_scale_factor
            x_end_real = x_end / np.abs(np.sin(angle_tmp * np.pi / 180.)) / z_scale_factor
            #yield from fly2d([fs, zebra, sclr1, xspress3],zpssy, y_start, y_end, y_num,
            #                 zpssz, x_start_real, x_end_real, x_num, exposure, return_speed=40)
            #RE(fly2d(zpssz, x_start_real, x_end_real, x_num, zpssy,
            #         y_start, y_end, y_num, exposure, return_speed=40))
            yield from fly2d(dets1, zps.zpssz,x_start_real, x_end_real, x_num,zps.zpssy,y_start,y_end,y_num,exposure, dead_time=0.005,return_speed = 100)
            plot2dfly(-1,elem,'sclr1_ch4')
            insertFig(note='zpsth = {}'.format(check_baseline(-1,'zpsth')))
            plt.close()
            yield from fly2d(dets1, zps.zpssz,x_start_real, x_end_real, x_num//2,zps.zpssy,y_start,y_end,y_num//2,exposure, dead_time=0.005,return_speed = 100)
            plot2dfly(-1,elem,'sclr1_ch4')
            insertFig(note='zpsth = {}'.format(check_baseline(-1,'zpsth')))
            plt.close()
            yield from fly2d(dets1, zps.zpssz,x_start_real, x_end_real, x_num//4,zps.zpssy,y_start,y_end,y_num//4,exposure, dead_time=0.005,return_speed = 100)
            plot2dfly(-1,elem,'sclr1_ch4')
            insertFig(note='zpsth = {}'.format(check_baseline(-1,'zpsth')))
            plt.close()
            #yield from bps.movr(smarx, x_offset_um/1000)
            #yield from bps.movr(smary,y_offset_um/1000)

        #mov_to_image_cen_smar(-1)
        #yield from mov_to_image_cen_dsx(-1)
        '''
        plot2dfly(-1,elem,'sclr1_ch4')
        insertFig(note='zpsth = {}'.format(check_baseline(-1,'zpsth')))
        plt.close()
        merlin1.unstage()
        xspress3.unstage()
        '''
        #print('waiting for 2 sec...')
        #yield from bps.sleep(5)
        #if np.remainder(i+1,5)==0:
        #    yield from peak_bpm_x(-20, 20, 10)
        #    yield from peak_bpm_y(-10, 10, 10)
    save_page()



    
def tomo_slice_scan(angle_start, angle_end, angle_num, x_start, x_end, x_num,
                    y_start, y_end, y_num, exposure):
    angle_start = float(angle_start)
    angle_end = float(angle_end)
    angle_num = int(angle_num)
    x_start = float(x_start)
    x_end = float(x_end)
    x_num = int(x_num)
    y_start = float(y_start)
    y_end = float(y_end)
    y_num = int(y_num)
    exposure = float(exposure)
    angle_step = (angle_end - angle_start) / angle_num

    y_step = (y_end - y_start) / y_num

    for j in range(y_num + 1):
        for i in range(angle_num + 1):
            angle = angle_start + i * angle_step
            mov(zpsth, angle)
            sleep(1)
            # mesh(zpssy,y_start,y_en,y_num,zpssx_lab,x_start,x_end,x_num,exposure)
            dscan(zpssx_lab, x_start, x_end, x_num, exposure)

            #print('waiting for 10 sec...')
            # sleep(10)
        movr(zpssy, y_step)

    mov(zpsth, 0)


def movr_zpz1(dz):
    yield from bps.movr(zp.zpz1, dz)
    #movr(zp.zpx, dz * 3.75)
    yield from bps.movr(zp.zpy, -dz*0.003091258+0.000236*dz-0.0010*dz+0.0016*dz-0.00128*dz+0.001*dz-0.0005*dz)
    yield from bps.movr(zp.zpx, (dz*0.003/40.33)+ dz*0.01/2.0-0.00496*dz+dz*0.001)

def mov_zpz1(pos):
    c_zpz1 = zp.zpz1.position
    dz = pos - c_zpz1
    yield from movr_zpz1(dz)

def reset_tpx(num):
    for i in range(1000):
        timepix2.cam.num_images.put(num, wait=False)
        sleep(0.5)



def th_fly1d(th_start, th_end, num, offset, mot, m_start, m_end, m_num, sec):
    
    th_step = (th_end - th_start) / num
    yield from bps.movr(zps.zpsth, th_start)
    yield from bps.sleep(5)
    
    '''
    yield from fly1d(dets1,zpssy, -2, 2, 200, 0.05)
    p1, p2 = erf_fit(-1,'zpssy','W_L')
    yield from bps.sleep(1)
    yield from bps.mov(zpssy,p1-offset)
    yield from bps.sleep(1)
    '''
    for i in range(num + 1):
        yield from fly1d(dets1, mot, m_start, m_end, m_num, sec)
        yield from bps.sleep(1)
        yield from bps.movr(zps.zpsth, th_step)
        yield from bps.sleep(1)
        '''
        yield from fly1d(dets1,zpssy, -2, 2, 200, 0.05)
        p1, p2 = erf_fit(-1,'zpssy','W_L')
        yield from bps.sleep(1)
        yield from bps.mov(zpssy,p1-offset)
        yield from bps.sleep(1)
        '''
    yield from bps.movr(zps.zpsth, -(th_end + th_step))
    yield from bps.sleep(2)



def move_fly_center(elem):
    scan_id, df = _load_scan(-1, fill_events=False)
    hdr = db[scan_id]['start']
    if elem in df:
        roi_data = np.asarray(df[elem])
    else:
        channels = [1, 2, 3]
        roi_keys = ['Det%d_%s' % (chan, elem) for chan in channels]
        for key in roi_keys:
            if key not in df:
                raise KeyError('ROI %s not found' % (key, ))
        roi_data = np.sum([getattr(df, roi) for roi in roi_keys], axis=0)

    scanned_axis = hdr['motor1']
    x = np.asarray(df[scanned_axis])
    nx = hdr['num1']
    ny = hdr['num2']
    roi_data = roi_data.reshape(ny,nx)
    x = x.reshape(ny,nx)
    ix,iy = ndimage.measurements.center_of_mass(roi_data)
    ix = int(ix)
    iy = int(iy)
    #i_max = find_mass_center(roi_data)
    #i_max = int(i_max)
    #print(ix,iy,x[ix,iy])
    #print(x)
    print('mass center:', x[ix,iy])
    #i_max = np.where(roi_data == np.max(roi_data))
    #mov(eval(scanned_axis),x[i_max[0]][0])

def mll_th_fly2d(th_start, th_end, num, mot1, x_start, x_end, x_num, mot2,y_start, y_end, y_num, sec):
    
    """relative theta"""
    
    #yield from shutter('open')
    init_th = dsth.position
    th_step = (th_end - th_start) / num
    th_pos = np.linspace(init_th + th_start,init_th + th_end, num+1)
    #yield from bps.movr(dsth, th_start)
    #yield from bps.movr(dssx, th_start)
    #fs.stage()
    #yield from bps.sleep(2)
    ic_0 = sclr2_ch4.get()
    #fs.unstage()


    for i in range(num + 1):
        yield from bps.mov(dsth,th_pos[i])
        while (sclr2_ch2.get() < 10000):
            yield from bps.sleep(60)
            print('IC3 is lower than 10000, waiting...')
        #fs.stage()
        #yield from bps.sleep(5)
        while (sclr2_ch4.get() < (0.7*ic_0)):
            yield from peak_bpm_y(-5,5,10)
            yield from peak_bpm_x(-15,15,10)
            ic_0 = sclr2_ch4.get()
        yield from bps.sleep(1)
        #fs.unstage()
        
        
        
        yield from fly1d(dets1,dssx,-6,6,100,0.05)
        cx = return_line_center(-1,'W_L',0.1)
        yield from bps.mov(dssx,cx)
        yield from bps.sleep(1)
        #yield from fly1d(dets1,dssy,-1.4,-0.8,100,0.05)
        #edge,fwhm = erf_fit(-1,'W_L')
        #cy = return_line_center(-1,'W_L',0.2)
        #if np.abs(edge + 1.15 - 0.4) > 0.25:
        #    yield from bps.mov(dssy,0.4)
        #else:
        #    yield from bps.mov(dssy,edge+1.15)
        #plt.close()
        #yield from bps.sleep(1)
        

        yield from fly2d(dets1, mot1, x_start, x_end, x_num, mot2, y_start, y_end, y_num, sec, return_speed=40)

        #yield from bps.movr(dssx,0.15)
        #yield from bps.movr(dssy,-0.09)
        print('2d scan done')
        bps.sleep(1)
        merlin1.unstage()
        xspress3.unstage()
        print('unstage detectors')
        bps.sleep(1)
        #plot_data(-1,'Ge')
        #yield from bps.sleep(2)
        #insertFig(note = 'dsth = {}'.format(check_baseline(-1,'dsth')))
        #yield from bps.sleep(2)

        #plt.close()
        print('executing image saving ...')
        try:
            #plot_img_sum(-1,threshold=[0,2000])
            #insertFig(note = f'dsth = {dsth.position :.3f}')
            #plt.close()

            plot_data(-1,'Cu')
            insertFig(note = f'dsth = {dsth.position :.3f}')
            plt.close()
        except:
            pass
        print('image saved')
        plt.close()
        #plot2dfly(-1,'Au_L')

        #yield from bps.movr(dsth, th_step)
        #yield from bps.movr(dssx,th_step)
    yield from bps.mov(dsth, init_th)
    #yield from bps.mov(dssx,init_x)
    save_page()
    #yield from shutter('close')


def zp_th_fly2d(th_start, th_end, num, mot1, x_start, x_end, x_num, mot2, y_start, y_end, y_num, sec,elem = 'Mn'):

    'move theta position relative and collect 2D scans'

    init_th = zpsth.position
    th_step = (th_end - th_start) / num
    yield from bps.movr(zpsth, th_start)
    ic_0 = sclr2_ch2.get()
    
    for i in tqdm.tqdm(range(num+1),desc = 'Theta Scan'):

        yield from check_for_beam_dump(5000)

        while (sclr2_ch2.get() < (0.8*ic_0)):
            yield from peak_bpm_y( -5, 5,10)
            yield from peak_bpm_x(-10,10,5)

        yield from fly1d(dets_fs,mot1,-8,8,200,0.1)
        #xc,fwhm=erf_fit(-1,elem,linear_flag=True)
        #except:pass
        #plt.close()
        xc = return_line_center(-1,elem,threshold=0.5, neg_flag=1)
        yield from bps.mov(mot1,xc+6)

        yield from fly1d(dets_fs,mot2,-10,10,200,0.1)
        yc = return_line_center(-1,elem,threshold=0.5)
        yield from bps.mov(mot2,yc)
        #yc,fwhm=erf_fit(-1,elem,linear_flag=True)
        
        #yield from bps.mov(mot2,yc+2)
        #yield from bps.movr(smary,(yc/1000)-0.002)
        #plt.close()
        #yield from bps.movr(smarx,(-10/1000))
        yield from bps.movr(mot1,-6)
        #plt.close()
        


        yield from fly2d(dets1, mot1, x_start, x_end, x_num, mot2, y_start, y_end, y_num, sec)

        yield from bps.sleep(1)
        xspress3.unstage()
        merlin1.unstage()
        #yield from bps.movr(smarx,(10/1000))
        

        try:
            #insert_diffSum_to_pdf(-1)

            insert_xrf_map_to_pdf(-1,elements = [elem],title_= ['zpsth', 'energy'])

        except:
            pass

        yield from bps.movr(zpsth, th_step)
        yield from bps.sleep(1)

        #yield from bps.movr(smarx,8/1000)
        #yield from bps.movr(smary,-6/1000)

    yield from bps.mov(zpsth, init_th)
    save_page()

    #yield from shutter('close'
    #<zp_th_fly2d(dets2,-0.5,0.5,10,zpssx, -10,10,100,zpssy,-6,6,60,0.05,-15,15,0,0,'Ni')



def th_fly2d(mot_th, th_start, th_end, num, mot1, x_start, x_end, x_num, mot2, y_start, y_end,
             y_num, sec):

    
    th_init = mot_th.position
    th_step = (th_end - th_start) / num
    yield from bps.movr(mot_th, th_start)
    #fs.stage()
    #yield from bps.sleep(2)
    #ic_0 = sclr2_ch4.get()
    #yield from bps.sleep(2)
    #fs.unstage()
    #yield from bps.sleep(2)
    for i in range(num + 1):

        #check_for_beam_dump(10000)
        while (sclr2_ch2.get() < 10000):
            yield from bps.sleep(60)
            print('IC3 is lower than 10000, waiting...')
        #fs.stage()
        #yield from bps.sleep(2)
        #if (sclr2_ch4.get() < (0.9*ic_0)):
        #    yield from peak_bpm_y(-5,5,10)
        #    yield from peak_bpm_x(-25,25,10)
        #    ic_0 = sclr2_ch4.get()

        #fs.unstage()

        '''
        yield from bps.mov(zpssx,0)
        yield from fly1d(dets1,zpssx,-15, 15, 200,0.03)
        corr_x_pos = return_line_center(-1,'Ge',0.2)
        #if abs(corr_x_pos-zpssx.position)< 5:
        yield from bps.mov(zpssx,corr_x_pos)
        yield from bps.mov(zpssy,0)
        yield from fly1d(dets1, zpssy, -5, 5, 100,0.03)
        edge, fwhm = erf_fit(-1,'Ge','sclr1_ch4',False)
        #if abs(edge+3.7) < 1:
        #    yield from bps.mov(dssy, edge-2.5)
        yield from bps.mov(zpssy,edge+1)
        '''

        #yield from bps.movr(dssx,0.125)
        yield from bps.sleep(2)
        yield from fly2d(dets1,mot1, x_start, x_end, x_num, mot2, y_start, y_end, y_num, sec)
        th_pos_1 = mot_th.position
        yield from bps.sleep(1)
        yield from bps.movr(mot_th, th_step)
        yield from bps.sleep(1)


        plot2dfly(-1, 'Ge', 'sclr1_ch4')
        insertFig(note = 'th = {:.3f}'.format(th_pos_1), title = ' ')
        plt.close(' ')
        plot_img_sum(-1,'merlin1')
        insertFig(note = 'th = {:.3f}'.format(th_pos_1), title = ' ')
        plt.close()

    yield from bps.mov(mot_th, th_init)
    save_page()

def th_dscan(m_th, th_start, th_end, num, mot, x_start, x_end, x_num, sec):
    #shutter('open')
    th_step = (th_end - th_start) / num
    yield from bps.movr(m_th, th_start)
    yield from bps.sleep(2)
    for i in range(num + 1):

        yield from fly1d(dets1,dssz,-1,1,100,0.1)
        tmp = return_line_center(-1, 'Ge')
        yield from bps.mov(dssz,tmp)
        yield from dscan(dets1, mot, x_start, x_end, x_num, sec)
        yield from bps.sleep(2)
        yield from bps.movr(m_th, th_step)
        yield from bps.sleep(2)
        plotScan(-1)
        yield from bps.sleep(2)
        insertFig(note = 'Oslo Dev 10',title ='ver. (dssy) vs. det row sum')
        plt.close()
        plot(-1,'Ge','sclr1_ch4')
        insertFig(note = 'Oslo',title ='Ge Fluorescence')
    yield from bps.movr(m_th, -(th_end + th_step))
    yield from bps.sleep(2)
    save_page()

    #example:th_fly2d(zpsth, 0,1,50,zpssx,-1,1,100,zpssy,-1,1,100,0.1)

def mll_th_fly1d(th_start, th_end, num, mot, x_start, x_end, x_num, sec):
    #shutter('open')
    th_int = dsth.position
    ic_0 = sclr2_ch4.get()
    th_step = (th_end - th_start) / num
    yield from bps.movr(dsth, th_start)
    yield from bps.sleep(1)
    for i in range(num + 1):
        #plt.close('all')

        while (sclr2_ch4.get() < 1000):
            yield from bps.sleep(60)
            print('IC3 is lower than 1000, waiting...')
        while (sclr2_ch4.get() < (0.9*ic_0)):
            yield from peak_bpm_y(-5,5,10)

        #yield from bps.sleep(1)
        #yield from fly1d(dets1,dssx, -1.2,1.2, 100, 0.1)
        #yield from bps.sleep(2)

        #tmp = return_line_center(-1, 'Ge')
        #tmp = erf_fit(-1, 'Ti')[0]-4
        #yield from bps.movr(dsx,tmp)
        #yield from bps.mov(dssx,tmp)
        #yield from bps.movr(dsy,2)

        yield from fly1d(dets1,dssy,-2,2, 400, 0.05)
        #yield from bps.sleep(2)
        tmp = return_line_center(-1, 'Ge',0.4)
        #tmp = erf_fit(-1, 'Ge')[0]
        yield from bps.mov(dssy,tmp)
        #yield from bps.mov(dssy,tmp)

        yield from fly1d(dets1, mot, x_start, x_end, x_num, sec,dead_time = 0.003)
        yield from bps.sleep(1)
        yield from bps.movr(dsth, th_step)
        #yield from bps.movr(dssx,4)
        #yield from bps.sleep(1)
        #plot_img_sum(-1)

        yield from bps.sleep(1)
        last_angle = check_baseline(-1,'dsth')
        plot(-1,'Ge','sclr1_ch4')
        #insertFig(note = 'Avatar',title ='dssy vs. det sum (dsth={})'.format(last_angle))
        insertFig(title = 'LiNbO3',note='dsth = {}'.format(check_baseline(-1,'dsth')))
        plt.close()
        plot_img_sum(-1, 'merlin1')
        insertFig(title = 'LiNbO3', note='dsth = {}'.format(check_baseline(-1,'dsth')))
        plt.close()

    yield from bps.mov(dsth, th_int)
    yield from bps.sleep(2)
    #yield from shutter('close')
    save_page()

def th_dscan(m_th, th_start, th_end, num, mot, x_start, x_end, x_num, sec):
    #shutter('open')
    th_step = (th_end - th_start) / num
    yield from bps.movr(m_th, th_start)
    yield from bps.sleep(2)
    for i in range(num + 1):

        yield from fly1d(dets1,dssz,-1,1,100,0.1)
        tmp = return_line_center(-1, 'Ge')
        yield from bps.mov(dssz,tmp)
        yield from dscan(dets1, mot, x_start, x_end, x_num, sec)
        yield from bps.sleep(2)
        yield from bps.movr(m_th, th_step)
        yield from bps.sleep(2)
        plotScan(-1)
        yield from bps.sleep(2)
        insertFig(note = 'Oslo Dev 10',title ='ver. (dssy) vs. det row sum')
        plt.close()
        plot(-1,'Ge','sclr1_ch4')
        insertFig(note = 'Oslo',title ='Ge Fluorescence')
    yield from bps.movr(m_th, -(th_end + th_step))
    yield from bps.sleep(2)
    save_page()

    #shutter('close')








def movr_zpsz_new(dist):
    movr(zps.zpsz,dist)
    movr(zps.smarx,dist*5.4161/1000.)
    movr(zps.smary,dist*1.8905/1000.)
def movr_smarz(dist):
    movr(zps.smarz, dist)
    movr(zps.smarx, dist*5.4161/1000.)
    movr(zps.smary, dist*1.8905/1000.)
def mll_movr_samp(angle, dx, dz):
    angle = angle*np.pi/180.0
    delta_x = (dx*np.cos(angle) - dz*np.sin(angle))
    delta_z = (dx*np.sin(angle) + dz*np.cos(angle))
    movr(smlld.dsx,delta_x)
    movr(smlld.dsz,delta_z)
def mll_movr_lab(dx, dz):
    angle = smlld.dsth.position
    angle = angle*np.pi/180.0
    delta_x = dx*np.cos(angle) - dz*np.sin(angle)
    delta_z = dx*np.sin(angle) + dz*np.cos(angle)
    yield from bps.movr(smlld.dsx, delta_x)
    yield from bps.movr(smlld.dsz, delta_z)
def zps_movr_lab(dx, dz):
    angle = zpsth.position
    angle = angle*np.pi/180.0
    delta_x = dx*np.cos(angle) - dz*np.sin(angle)
    delta_z = dx*np.sin(angle) + dz*np.cos(angle)
    yield from bps.movr(smarx, delta_x/1000.)
    yield from bps.movr(smarz, delta_z/1000.)

def mll_movr_samp_test(angle_offset,dist):
    angle_offset = -1 * angle_offset
    angle = smlld.dsth.position

    if np.abs(angle) <= 45.:
        alpha = (90 - angle - angle_offset) * np.pi / 180.
        beta = (90 + angle) * np.pi / 180.
        delta_x = -1 * np.sin(beta) * dist / np.sin(alpha) * np.cos(angle_offset)
        delta_z = np.sin(beta) * dist / np.sin(alpha) * np.sin(angle_offset)
    else:
        alpha = -1*(90 - angle - angle_offset) * np.pi / 180.
        beta = (180 - angle) * np.pi / 180.

        delta_x = -1 * np.sin(beta) * dist / np.sin(alpha) * np.cos(angle_offset)
        delta_z = np.sin(beta) * dist / np.sin(alpha) * np.sin(angle_offset)

    movr(smlld.dsx, delta_x)
    movr(smlld.dsz, delta_z)
def zp_movr_samp(th, dx, dz):
    th = th*np.pi/180.0
    delta_x = dx*np.cos(th) - dz*np.sin(th)
    delta_z = dx*np.sin(th) + dz*np.cos(th)
    movr(smarx, delta_x)
    movr(smarz, delta_z)


def zp_movr_lab(dx, dz):
    angle = zps.zpsth.position
    angle = angle*np.pi/180.0
    #angle = 14.2*np.pi/180
    delta_x = dx*np.cos(angle) - dz*np.sin(angle)
    delta_z = dx*np.sin(angle) + dz*np.cos(angle)
    movr(smarx, delta_x)
    movr(smarz, delta_z)


def multi_pos_scan(scan_list,
                   x_range_list, x_num_list,
                   y_range_list, y_num_list,
                   exp_list):
    """
    Parameters
    ----------
    scan_list : list
         list of pre-idetifed locations as scan_id

    x_range_list, y_range_list : list
         list of scanwidth, scan +/- value/2 for each point

    x_num_list, y_num_list : list
         Number of points at each scan location in

    exp_list : list
         Exposure time per location
    """
    for i, (scan, x_range, x_num, y_range, y_num, exposure) in enumerate(
            zip(scan_list, x_range_list, x_num_list, y_range_list, y_num_list, exp_list)):
        print('scan ', i, ' move to #', scan, 'position')
        # TODO make this a plan
        recover_mll_scan_pos(int(scan))
        sleep(0.5)
        RE(fly2d(dssx,
                 -x_range/2, x_range/2, x_num,
                 dssy,
                 -y_range/2, y_range/2, y_num,
                 exposure))
        sleep(0.5)

def multi_pos_scan_plan(scan_list,
                        x_range_list, x_num_list,
                        y_range_list, y_num_list,
                        exp_list):
    """
    Parameters
    ----------
    scan_list : list
         list of pre-idetifed locations as scan_id

    x_range_list, y_range_list : list
         list of scanwidth, scan +/- value/2 for each point

    x_num_list, y_num_list : list
         Number of points at each scan location in

    exp_list : list
         Exposure time per location
    """
    for i, (scan, x_range, x_num, y_range, y_num, exposure) in enumerate(
            zip(scan_list, x_range_list, x_num_list, y_range_list, y_num_list, exp_list)):
        print('scan ', i, ' move to #', scan, 'position')
        yield from recover_mll_scan_pos_plan(int(scan))
        yield from fly2d(dssx,
                         -x_range/2, x_range/2, x_num,
                         dssy,
                         -y_range/2, y_range/2, y_num,
                         exposure)

def smll_kill_piezos():
    # smll.kill.put(1)
    yield from bps.mv(smll.kill, 1)
    yield from bps.sleep(5)

def smll_zero_piezos():
    # smll.zero.put(1)
    yield from bps.mv(smll.zero, 1)
    yield from bps.sleep(3)

def smll_sync_piezos():
    #sync positions
    yield from bps.mov(ssx, smll.ssx.position + 0.0001)
    yield from bps.mov(ssy, smll.ssy.position + 0.0001)
    yield from bps.mov(ssz, smll.ssz.position + 0.0001)

def movr_sx(dist):
    alpha = 15*np.pi/180.0
    c_ssx = smll.ssx.position
    c_ssy = smll.ssy.position
    c_ssz = smll.ssz.position

    print('Current ssx = %.3f' % c_ssx)
    print('Current ssy = %.3f' % c_ssy)
    print('Current ssz = %.3f' % c_ssz)

    yield from smll_kill_piezos()

    t_ssx = c_ssx + dist

    dxp = t_ssx - smll.ssx.position
    dzp = c_ssz - smll.ssz.position

    dx, dz = sample_to_lab(dxp, dzp, alpha)

    yield from bps.movr(sx, dx)
    yield from bps.movr(sz, dz)

    dy = c_ssy -smll.ssy.position

    yield from bps.movr(sy, dy)

    yield from bps.sleep(5)

    yield from smll_sync_piezos()

    yield from bps.mov(ssx, t_ssx)
    yield from bps.mov(ssy, c_ssy)
    yield from bps.mov(ssz, c_ssz)

    print('Post-move x = %.3f' % smll.ssx.position)
    print('Post-move y = %.3f' % smll.ssy.position)
    print('Post-move z = %.3f' % smll.ssz.position)

def mov_sx(t_pos):
    alpha = 15*np.pi/180.0
    c_ssx = smll.ssx.position
    c_ssy = smll.ssy.position
    c_ssz = smll.ssz.position

    print('Current ssx = %.3f' % c_ssx)
    print('Current ssy = %.3f' % c_ssy)
    print('Current ssz = %.3f' % c_ssz)

    yield from smll_kill_piezos()

    t_ssx = t_pos

    dxp = t_ssx - smll.ssx.position
    dzp = c_ssz - smll.ssz.position

    dx, dz = sample_to_lab(dxp, dzp, alpha)

    yield from bps.movr(sx, dx)
    yield from bps.movr(sz, dz)

    dy = c_ssy - smll.ssy.position

    yield from bps.movr(sy, dy)

    yield from bps.sleep(5)

    yield from smll_sync_piezos()
    yield from bps.mov(ssx, t_ssx)
    yield from bps.mov(ssy, c_ssy)
    yield from bps.mov(ssz, c_ssz)

    print('Post-move x = %.3f' % (smll.ssx.position))
    print('Post-move y = %.3f' % (smll.ssy.position))
    print('Post-move z = %.3f' % (smll.ssz.position))


def movr_sy(dist):
    alpha = 15*np.pi/180.0
    c_ssx = smll.ssx.position
    c_ssy = smll.ssy.position
    c_ssz = smll.ssz.position

    print('Current ssx = %.3f' % c_ssx)
    print('Current ssy = %.3f' % c_ssy)
    print('Current ssz = %.3f' % c_ssz)

    yield from smll_kill_piezos()

    t_ssy = c_ssy + dist
    dy = t_ssy - smll.ssy.position
    yield from bps.movr(sy, dy)

    dxp = c_ssx - smll.ssx.position
    dzp = c_ssz - smll.ssz.position

    dx, dz = sample_to_lab(dxp, dzp, alpha)

    yield from bps.movr(sx, dx)
    yield from bps.movr(sz, dz)

    yield from bps.sleep(5)

    yield from smll_sync_piezos()
    yield from bps.mov(ssy, t_ssy)
    yield from bps.mov(ssz, c_ssz)
    yield from bps.mov(ssx, c_ssx)

    print('Post-move x = %.3f' % smll.ssx.position)
    print('Post-move y = %.3f' % smll.ssy.position)
    print('Post-move z = %.3f' % smll.ssz.position)

def mov_sy(t_pos):
    alpha = 15*np.pi/180.0
    c_ssx = smll.ssx.position
    c_ssy = smll.ssy.position
    c_ssz = smll.ssz.position

    print('Current ssx = %.3f' % c_ssx)
    print('Current ssy = %.3f' % c_ssy)
    print('Current ssz = %.3f' % c_ssz)

    yield from smll_kill_piezos()

    t_ssy = t_pos
    dy = t_ssy - smll.ssy.position
    yield from bps.movr(sy, dy)

    dxp = c_ssx - smll.ssx.position
    dzp = c_ssz - smll.ssz.position

    dx, dz = sample_to_lab(dxp, dzp, alpha)

    yield from bps.movr(sbx, dx)
    yield from bps.movr(sbz, dz)

    yield from bps.sleep(5)

    yield from smll_sync_piezos()
    yield from bps.mov(ssx, c_ssx)
    yield from bps.mov(ssy, t_ssy)
    yield from bps.mov(ssz, c_ssz)

    print('Post-move x = %.3f' % (smll.ssx.position))
    print('Post-move y = %.3f' % (smll.ssy.position))
    print('Post-move z = %.3f' % (smll.ssz.position))

def movr_sz(dist):
    alpha = 15.0*np.pi/180

    c_ssz = smll.dssz.position
    c_ssy = smll.dssy.position
    c_ssx = smll.dssx.position

    print('Current ssx = %.3f' % c_ssx)
    print('Current ssy = %.3f' % c_ssy)
    print('Current ssz = %.3f' % c_ssz)

    yield from smll_kill_piezos()

    t_ssz = c_ssz + dist*np.cos(alpha)
    dz = t_ssz - smll.dssz.position
    dy = c_ssy - smll.dssy.position

    yield from bps.movr(sbz, dz)
    yield from bps.movr(dsy, dy/1000.0)

    yield from bps.sleep(5)

    yield from smll_sync_piezos()
    yield from bps.mov(dssy, c_ssy)
    yield from bps.mov(dssz, t_ssz)

    print('post-move x = %.3f' % smll.dssx.position)
    print('Post-move y = %.3f' % smll.dssy.position)
    print('Post-move z = %.3f' % smll.dssz.position)

def mov_sz(t_pos):
    alpha = 15.0*np.pi/180

    c_ssz = smll.ssz.position
    c_ssy = smll.ssy.position
    c_ssx = smll.ssx.position

    print('Current ssx = %.3f' % c_ssx)
    print('Current ssy = %.3f' % c_ssy)
    print('Current ssz = %.3f' % c_ssz)

    yield from smll_kill_piezos()

    t_ssz = t_pos
    dz = (t_ssz - smll.ssz.position)/np.cos(alpha)
    dy = c_ssy - smll.ssy.position

    yield from bps.movr(sz, dz)
    yield from bps.movr(sy, dy)

    yield from bps.sleep(5)

    yield from smll_sync_piezos()
    yield from bps.mov(ssy, c_ssy)
    yield from bps.mov(ssz, t_ssz)

    print('Post-move x = %.3f' % smll.ssx.position)
    print('Post-move y = %.3f' % smll.ssy.position)
    print('Post-move z = %.3f' % smll.ssz.position)

def list_fly2d(x_pos, y_pos, scan_p):
    if np.size(x_pos) != np.size(y_pos):
        raise KeyError('size of x_pos list is not equal to that of y_pos list')
    else:
        num_pos = np.size(x_pos)
    if np.size(scan_p) != 7:
        raise KeyError('Last argument needs 7 numbers')
    else:
        for i in range(num_pos):
            mov_sx(x_pos[i])
            mov_sy(y_pos[i])
            RE(fly2d(ssx, scan_p[0], scan_p[1], scan_p[2], ssy, scan_p[3], scan_p[4], scan_p[5], scan_p[6], return_speed=20))
            plot2dfly(-1, 'Ca', 'sclr1_ch4')
            peak_ic()
            sleep(2)


def save_wh_pos(print_flag=False):
    class Tee(object):
        def __init__(self, *files):
            self.files = files
        def write(self, obj):
            for f in self.files:
                f.write(obj)
                f.flush() # If you want the output to be visible immediately
        def flush(self) :
            for f in self.files:
                f.flush()

    now = datetime.now()
    fn = '/data/motor_positions/log-'+np.str(now.year)+'-'+np.str(now.month)+'-'+np.str(now.day)+'-'+np.str(now.hour)+'-'+np.str(now.minute)+'.log'
    f = open(fn,'w')
    original = sys.stdout
    sys.stdout = Tee(sys.stdout, f)
    wh_pos()
    sys.stdout = original
    f.close()
    if print_flag:
        shutil.copyfile(fn,'/data/motor_positions/tmp.log')
        os.system("lp -o cpi=20 -o lpi=8 -o media='letter' -d HXN-printer-1 /data/motor_positions/tmp.log")


def zps_kill_piezos():
    zps.kill.put(1)
    yield from bps.sleep(5)

def zps_zero_piezos():
    zps.zero.put(1)
    yield from bps.sleep(3)

def zps_sync_piezos():
    #sync positions
    yield from bps.mov(zps.zpssx, zps.zpssx.position + 0.0001)
    yield from bps.mov(zps.zpssy, zps.zpssy.position + 0.0001)
    yield from bps.mov(zps.zpssz, zps.zpssz.position + 0.0001)


def movr_zpsx(dist):
    alpha = 0.0*np.pi/180.0
    c_ssx = zps.zpssx.position
    c_ssy = zps.zpssy.position
    c_ssz = zps.zpssz.position

    print('Current ssx = %.3f' % c_ssx)
    print('Current ssy = %.3f' % c_ssy)
    print('Current ssz = %.3f' % c_ssz)

    zps_kill_piezos()

    t_ssx = c_ssx + dist

    dxp = t_ssx - zps.zpssx.position
    dzp = c_ssz - zps.zpssz.position

    dx, dz = sample_to_lab(dxp, dzp, alpha)
    dx = dx/1000.
    dz = dz/1000.

    movr(zps.zpsx, dx)
    movr(zps.zpsz, dz)

    dy = c_ssy -zps.zpssy.position
    dy = dy/1000.

    movr(smary, dy)

    sleep(5)

    zps_sync_piezos()

    mov(zps.zpssx, t_ssx)
    mov(zps.zpssy, c_ssy)
    mov(zps.zpssz, c_ssz)

    print('Post-move x = %.3f' % zps.zpssx.position)
    print('Post-move y = %.3f' % zps.zpssy.position)
    print('Post-move z = %.3f' % zps.zpssz.position)

def mov_zpsx(t_pos):
    alpha = 0.0*np.pi/180.0
    c_ssx = zps.zpssx.position
    c_ssy = zps.zpssy.position
    c_ssz = zps.zpssz.position

    print('Current zpssx = %.3f' % c_ssx)
    print('Current zpssy = %.3f' % c_ssy)
    print('Current zpssz = %.3f' % c_ssz)

    zps_kill_piezos()

    t_ssx = t_pos

    dxp = t_ssx - zps.zpssx.position
    dzp = c_ssz - zps.zpssz.position

    dx, dz = sample_to_lab(dxp, dzp, alpha)
    dx = dx/1000.0
    dz = dz/1000.0

    movr(zps.zpsx, dx)
    movr(zps.zpsz, dz)

    dy = c_ssy - zps.zpssy.position
    dy = dy/1000.0

    movr(smary, dy)

    sleep(5)

    zps_sync_piezos()
    mov(zps.zpssx, t_ssx)
    mov(zps.zpssy, c_ssy)
    mov(zps.zpssz, c_ssz)

    print('Post-move x = %.3f' % (zps.zpssx.position))
    print('Post-move y = %.3f' % (zps.zpssy.position))
    print('Post-move z = %.3f' % (zps.zpssz.position))


def movr_zpsy(dist):
    alpha = 0.0*np.pi/180.0
    c_ssx = zps.zpssx.position
    c_ssy = zps.zpssy.position
    c_ssz = zps.zpssz.position

    print('Current zpssx = %.3f' % c_ssx)
    print('Current zpssy = %.3f' % c_ssy)
    print('Current zpssz = %.3f' % c_ssz)

    zps_kill_piezos()

    t_ssy = c_ssy + dist
    dy = t_ssy - zps.zpssy.position
    dy = dy/1000.0

    movr(smary, dy)

    dxp = c_ssx - zps.zpssx.position
    dzp = c_ssz - zps.zpssz.position

    dx, dz = sample_to_lab(dxp, dzp, alpha)
    dx = dx/1000.0
    dz = dz/1000.0

    movr(zps.zpsx, dx)
    movr(zps.zpsz, dz)

    sleep(5)

    zps_sync_piezos()
    mov(zps.zpssx, c_ssx)
    mov(zps.zpssy, t_ssy)
    mov(zps.zpssz, c_ssz)

    print('Post-move x = %.3f' % zps.zpssx.position)
    print('Post-move y = %.3f' % zps.zpssy.position)
    print('Post-move z = %.3f' % zps.zpssz.position)

def mov_zpsy(t_pos):
    alpha = 0.0*np.pi/180.0
    c_ssx = zps.zpssx.position
    c_ssy = zps.zpssy.position
    c_ssz = zps.zpssz.position

    print('Current zpssx = %.3f' % c_ssx)
    print('Current zpssy = %.3f' % c_ssy)
    print('Current zpssz = %.3f' % c_ssz)

    zps_kill_piezos()

    t_ssy = t_pos
    dy = t_ssy - zps.zpssy.position
    dy = dy/1000.0

    movr(smary, dy)

    dxp = c_ssx - zps.zpssx.position
    dzp = c_ssz - zps.zpssz.position

    dx, dz = sample_to_lab(dxp, dzp, alpha)
    dx = dx/1000.0
    dz = dz/1000.0

    movr(zps.zpsx, dx)
    movr(zps.zpsz, dz)

    sleep(5)

    zps_sync_piezos()
    mov(zps.zpssx, c_ssx)
    mov(zps.zpssy, t_ssy)
    mov(zps.zpssz, c_ssz)

    print('Post-move x = %.3f' % (zps.zpssx.position))
    print('Post-move y = %.3f' % (zps.zpssy.position))
    print('Post-move z = %.3f' % (zps.zpssz.position))

def movr_zpsz(dist):
    alpha = 0.0*np.pi/180

    c_ssz = zps.zpssz.position
    c_ssy = zps.zpssy.position
    c_ssx = zps.zpssx.position

    print('Current zpssx = %.3f' % c_ssx)
    print('Current zpssy = %.3f' % c_ssy)
    print('Current zpssz = %.3f' % c_ssz)

    zps_kill_piezos()

    t_ssz = c_ssz + dist*np.cos(alpha)
    dz = t_ssz - zps.zpssz.position
    dy = c_ssy - zps.zpssy.position
    dx = c_ssx - zps.zpssx.position

    dz = dz/1000.0
    dy = dy/1000.0
    dx = dx/1000.0

    movr(zps.zpsz, dz)
    movr(smary, dy)
    movr(zps.zpsx, dx)

    sleep(5)

    zps_sync_piezos()
    mov(zpssy, c_ssy)
    mov(zpssz, t_ssz)
    mov(zpssx, c_ssx)

    print('post-move x = %.3f' % zps.zpssx.position)
    print('Post-move y = %.3f' % zps.zpssy.position)
    print('Post-move z = %.3f' % zps.zpssz.position)

def mov_zpsz(t_pos):
    alpha = 0.0*np.pi/180

    c_ssz = zps.zpssz.position
    c_ssy = zps.zpssy.position
    c_ssx = zps.zpssx.position

    print('Current zpssx = %.3f' % c_ssx)
    print('Current zpssy = %.3f' % c_ssy)
    print('Current zpssz = %.3f' % c_ssz)

    zps_kill_piezos()

    t_ssz = t_pos
    dz = (t_ssz - zps.zpssz.position)/np.cos(alpha)
    dy = c_ssy - zps.zpssy.position
    dx = c_ssx - zps.zpssx.position

    dx = dx/1000.0
    dy = dy/1000.0
    dz = dz/1000.0

    movr(zps.zpsz, dz)
    movr(smary, dy)
    movr(zps.zpsx, dx)

    sleep(5)

    zps_sync_piezos()

    mov(zpssy, c_ssy)
    mov(zpssz, t_ssz)
    mov(zpssx, c_ssx)

    print('Post-move x = %.3f' % zps.zpssx.position)
    print('Post-move y = %.3f' % zps.zpssy.position)
    print('Post-move z = %.3f' % zps.zpssz.position)


def plot_fermat(scan_id,elem='Ga',norm=1):
    df = db.get_table(db[scan_id],fill=False)
    x = np.asarray(df.zpssx)
    y = np.asarray(df.zpssy)
    io = np.asfarray(df.sclr1_ch4)
    #if elem == 'Ga':
    xrf = np.asfarray(eval('df.Det1_'+elem)) + np.asfarray(eval('df.Det2_'+elem)) + np.asfarray(eval('df.Det3_'+elem))
    #elif elem == 'K':
    #    xrf = np.asfarray(df.Det1_K) + np.asfarray(df.Det2_K) + np.asfarray(df.Det3_K)

    if norm:
        xrf /= (io+1.e-8)
        #print(xrf.dtype)
    props = dict(alpha=0.8, edgecolors='none' )
    plt.figure()
    plt.scatter(x,y,c=xrf,s=50,marker='s',**props)
    plt.xlim([np.min(x),np.max(x)])
    plt.ylim([np.min(y),np.max(y)])
    plt.title('scan '+ np.str(scan_id))
    plt.axes().set_aspect('equal')
    plt.gca().invert_yaxis()
    plt.colorbar()

    plt.show()


def return_center_of_mass(scan_id = -1, elem = 'Cr',th=0.5):
    df2 = db.get_table(db[scan_id],fill=False)
    xrf = np.asfarray(eval('df2.Det2_' + elem)) + np.asfarray(eval('df2.Det1_' + elem)) + np.asfarray(eval('df2.Det3_' + elem))
    motors = db[scan_id].start['motors']
    x = np.array(df2[motors[0]])
    y = np.array(df2[motors[1]])
    #I0 = np.asfarray(df2.sclr1_ch4)
    I0 = np.asfarray(df2['sclr1_ch4'])
    if I0[0]==0:
        I0[0]=I0[1]
    scan_info=db[scan_id]
    tmp = scan_info['start']
    nx=tmp['plan_args']['num1']
    ny=tmp['plan_args']['num2']

    xrf = xrf/I0
    xrf = np.asarray(np.reshape(xrf,(ny,nx)))
    tth = th*np.max(xrf)
    xrf[xrf < tth] = 0
    #xrf[xrf >= th] = 1

    b = ndimage.measurements.center_of_mass(xrf)

    iy = int(np.round(b[0]))
    ix = int(np.round(b[1]))
    i_max = ix + iy * nx

    x_cen = x[i_max]
    y_cen = y[i_max]
    return (x_cen, y_cen)

def return_center_of_mass_blurr(scan_id = -1, elem = 'Cr',blurr_level = 10,bitflag=1):
    df2 = db.get_table(db[scan_id],fill=False)
    xrf = np.asfarray(eval('df2.Det2_' + elem)) + np.asfarray(eval('df2.Det1_' + elem)) + np.asfarray(eval('df2.Det3_' + elem))
    motors = db[scan_id].start['motors']
    x = np.array(df2[motors[0]])
    y = np.array(df2[motors[1]])
    #I0 = np.asfarray(df2.sclr1_ch4)
    I0 = np.asfarray(df2['sclr1_ch4'])
    scan_info=db[scan_id]
    tmp = scan_info['start']
    nx=tmp['plan_args']['num1']
    ny=tmp['plan_args']['num2']

    xrf = xrf/I0
    xrf = np.asarray(np.reshape(xrf,(ny,nx)))

    if bitflag:
        xrf[xrf <= 0.9*np.max(xrf)] = 0.
        xrf[xrf > 0.9*np.max(xrf)] = 1.
    xrf = gaussian_filter(xrf,blurr_level)

    b = ndimage.measurements.center_of_mass(xrf)

    iy = int(np.round(b[0]))
    ix = int(np.round(b[1]))
    i_max = ix + iy * nx

    x_cen = x[i_max]
    y_cen = y[i_max]
    return (x_cen, y_cen)


def mov_to_image_cen_corr_dsx(scan_id=-1, elem='Pt',bitflag=1, moveflag=1):
    print(scan_id)
    image_ref = retreat_xrf_roi(scan_id-2, elem,bitflag)
    image = retreat_xrf_roi(scan_id,elem,bitflag)
    corr = signal.correlate2d(image_ref, image, boundary='symm', mode='same')
    #nx,ny = np.shape(image)
    max_y,max_x = np.where(corr == np.max(corr))

    df2 = db.get_table(db[scan_id],fill=False)
    hdr = db[scan_id]['start']
    x_motor = hdr['motor1']
    y_motor = hdr['motor2']
    x = np.asarray(df2[x_motor])
    y = np.asarray(df2[y_motor])

    scan_info=db[scan_id]
    tmp = scan_info['start']
    nx=tmp['plan_args']['num1']
    ny=tmp['plan_args']['num2']

    step_x_um = (hdr['scan_end1'] - hdr['scan_start1']) / nx
    step_y_um = (hdr['scan_end2'] - hdr['scan_start2']) / ny


    dx_um = -1*(max_x - nx/2) * step_x_um
    dy_um = -1*(max_y - ny/2) * step_y_um

    if x_motor == 'dssx':
        print('move dsx by', -dx_um)
        if moveflag:
            if np.abs(dx_um)>step_x_um:
                movr(smlld.dsx, -dx_um)

    if x_motor == 'dssz':
        print('move dsz by', dx_um)
        if moveflag:
            if np.abs(dx_um)>step_x_um:
                movr(smlld.dsz, dx_um)

    '''
    image_ref_crop = image_ref[:,nx/4:nx*3/4]
    image_crop = image[:,nx/4:nx*3/4]
    corr_crop = signal.correlate2d(image_ref_crop, image_crop, boundary='symm', mode='same')
    max_y_crop,max_x_crop = np.where(corr_crop == np.max(corr_crop))
    dy_um_crop = -1*(max_y_crop - ny/2) * step_y_um
    plt.figure()
    plt.subplot(221)
    plt.imshow(image_ref_crop)
    plt.subplot(222)
    plt.imshow(image_crop)
    plt.subplot(223)
    plt.imshow(corr_crop)
    plt.show()
    '''

    ly_ref = np.sum(image_ref,axis=1)
    ly = np.sum(image,axis=1)
    corr_1d = np.correlate(np.squeeze(ly_ref),np.squeeze(ly),'same')
    max_y= np.where(corr_1d == np.max(corr_1d))
    #print(max_y)
    dy_um = -1*(max_y[0] - ny/2) * step_y_um
    '''
    plt.figure()
    plt.subplot(311)
    plt.plot(ly_ref)
    plt.subplot(312)
    plt.plot(ly)
    plt.subplot(313)
    plt.plot(corr_1d)
    plt.show()
    '''
    print('move y by', dy_um*0.001)
    if moveflag:
        #if np.abs(dy_um)>step_y_um:
        movr(smlld.dsy, dy_um*0.001)



def mov_to_image_cen_dsx(scan_id=-1, elem='Ni', bitflag=1, moveflag=1,piezomoveflag=1,x_offset=0,y_offset=0):

    df2 = db.get_table(db[scan_id],fill=False)
    xrf = np.asfarray(eval('df2.Det2_' + elem)) + np.asfarray(eval('df2.Det1_' + elem)) + np.asfarray(eval('df2.Det3_' + elem))
    #xrf_Pt = np.asfarray(eval('df2.Det2_' + 'Ni')) + np.asfarray(eval('df2.Det1_' + 'Ni')) + np.asfarray(eval('df2.Det3_' + 'Ni'))
    hdr = db[scan_id]['start']
    x_motor = hdr['motor1']
    y_motor = hdr['motor2']
    x = np.asarray(df2[x_motor])
    y = np.asarray(df2[y_motor])
    I0 = np.asfarray(df2.sclr1_ch4)

    scan_info=db[scan_id]
    tmp = scan_info['start']
    nx=tmp['plan_args']['num1']
    ny=tmp['plan_args']['num2']

    xrf = xrf/I0
    xrf = np.asarray(np.reshape(xrf,(ny,nx)))

    '''
    xrf_Pt = xrf_Pt/I0
    index_Pt = np.where(xrf_Pt == np.max(xrf_Pt))
    Pt_max_y = y[index_Pt]
    Pt_max_x = x[index_Pt]
    Pt_max_target_y = -0.5
    Pt_max_target_x = 0
    '''
    #x_offset = 0
    #y_offset = -2.5
 #   print('move dsy by', Pt_max_target_y-Pt_max_y)

 #   movr(smlld.dsy,-1.*(Pt_max_target_y-Pt_max_y)*1.e-3)


    #plt.figure()
    #plt.imshow(xrf)

    if bitflag:
        xrf[xrf <= 0.2*np.max(xrf)] = 0.
        xrf[xrf > 0.2*np.max(xrf)] = 1.

    b = ndimage.measurements.center_of_mass(xrf)

    iy = int(np.round(b[0]))
    ix = int(np.round(b[1]))
    i_max = ix + iy * nx

    x_cen = x[i_max]
    y_cen = y[i_max]

    print(b,ix,iy,i_max,x_cen,y_cen)
    # if moveflag:
        # movr(smlld.dsy,y_cen/1000.)

    if x_motor == 'dssx':
        # print('move dsz,by', Pt_max_x-Pt_max_target_x, 'um')
        #print('move dsx by', 1*(x_cen - target_x))
        if moveflag:
            if piezomoveflag:
                print('move dssx to', (x_cen+x_offset))
                yield from bps.mov(smlld.dssx,(x_cen+x_offset))
            else:
                yield from bps.movr(smlld.dsx, -1.*(x_cen+x_offset))
            #movr(smlld.dsz, Pt_max_x-Pt_max_target_x)
            #mov(zps.zpssx,0)
        yield from bps.sleep(.1)

    elif x_motor == 'dssz':
        #print('move dsx,by', -1*(Pt_max_x-Pt_max_target_x) , 'um')
        print('x center ',x_cen)
        #print('move dsz by', (x_cen+x_offset))
        if moveflag:
            if piezomoveflag:
                print('move dssz to', (x_cen+x_offset))
                yield from bps.mov(smlld.dssz,(x_cen + x_offset))
            else:
                print('move dsz by', (x_cen+x_offset))
                yield from bps.movr(smlld.dsz, (x_cen + x_offset))
#        movr(smlld.dsx, -1*(Pt_max_x-Pt_max_target_x))
        #mov(zps.zpssx,0)
    yield from bps.sleep(.1)

    if moveflag:
        print('y center', y_cen)
        if piezomoveflag:
            print('move dssy to:', (y_cen +y_offset)*0.001)
            yield from bps.mov(smlld.dssy,(y_cen - y_offset))
        else:
            #movr(smlld.dsy, y_cen*0.001)
            print('move dsy by:', (y_cen +y_offset)*0.001)
            yield from bps.movr(smlld.dsy, (y_cen + y_offset)*0.001)
    #mov(zps.zpssy,0)
    yield from bps.sleep(.1)



def calc_image_cen_smar(scan_id=-1, elem='Er', bitflag=1, movflag=1):

    df2 = db.get_table(db[scan_id],fill=False)
    xrf = np.asfarray(eval('df2.Det2_' + elem)) + np.asfarray(eval('df2.Det1_' + elem)) + np.asfarray(eval('df2.Det3_' + elem))
    hdr = db[scan_id]['start']
    x_motor = hdr['motor1']
    y_motor = hdr['motor2']
    x = np.asarray(df2[x_motor])
    y = np.asarray(df2[y_motor])
    I0 = np.asfarray(df2.sclr1_ch4)

    scan_info=db[scan_id]
    tmp = scan_info['start']
    nx=tmp['plan_args']['num1']
    ny=tmp['plan_args']['num2']

    xrf = xrf/I0

    if bitflag:
        coe=0.6
        xrf[xrf <= coe*np.max(xrf)] = 0.
        xrf[xrf > coe*np.max(xrf)] = 1.
        xrf = np.asarray(np.reshape(xrf,(ny,nx)))


    else:
        xrf = np.asarray(np.reshape(xrf,(ny,nx)))

    b = ndimage.measurements.center_of_mass(xrf)

    iy = int(np.round(b[0]))
    ix = int(np.round(b[1]))
    i_max = ix + iy * nx

    x_cen = x[i_max]
    y_cen = y[i_max]

    cen=[x_cen,y_cen]
    return cen

def mov_to_image_cen_smar(scan_id=-1, elem='Er', bitflag=1, movflag=1):

    df2 = db.get_table(db[scan_id],fill=False)
    xrf = np.asfarray(eval('df2.Det2_' + elem)) + np.asfarray(eval('df2.Det1_' + elem)) + np.asfarray(eval('df2.Det3_' + elem))
    hdr = db[scan_id]['start']
    x_motor = hdr['motor1']
    y_motor = hdr['motor2']
    x = np.asarray(df2[x_motor])
    y = np.asarray(df2[y_motor])
    I0 = np.asfarray(df2.sclr1_ch4)

    scan_info=db[scan_id]
    tmp = scan_info['start']
    nx=tmp['plan_args']['num1']
    ny=tmp['plan_args']['num2']

    xrf = xrf/I0
#    xrf = np.asarray(np.reshape(xrf,(ny,nx)))

    #plt.figure()
    #plt.imshow(xrf)

    if bitflag:
        coe=0.6
        xrf[xrf <= coe*np.max(xrf)] = 0.
        xrf[xrf > coe*np.max(xrf)] = 1.
        xrf = np.asarray(np.reshape(xrf,(ny,nx)))


    else:
        xrf = np.asarray(np.reshape(xrf,(ny,nx)))

    b = ndimage.measurements.center_of_mass(xrf)

    iy = int(np.round(b[0]))
    ix = int(np.round(b[1]))
    i_max = ix + iy * nx

    x_cen = x[i_max]
    y_cen = y[i_max]
    return (x_cen,y_cen)


    #print(b,ix,iy,i_max,x_cen,y_cen)

    if x_motor == 'zpssx':
        print('move smarx,by', x_cen, 'um')
        #print('move zpssx, zpssy to ',0, 0)
        if movflag:
           yield from bps.movr(zps.smarx, x_cen*0.001)
        #mov(zps.zpssx,0)
        bps.sleep(.1)

    elif x_motor == 'zpssz':
        print('move smarz,by', x_cen, 'um')
        if movflag:
            yield from bps.movr(zps.smarz, x_cen*0.001)
        #mov(zps.zpssx,0)
        bps.sleep(.1)
#    print('move smary,by', y_cen, 'um')
#    if movflag:
#        movr(zps.smary, y_cen*0.001)
    #mov(zps.zpssy,0)
    bps.sleep(.1)


def mov_to_line_center(scan_id=-1,elem='Ga',threshold=0,moveflag=0,movepiezoflag=0):
    df2 = db.get_table(db[scan_id],fill=False)
    xrf = np.asfarray(eval('df2.Det2_' + elem)) + np.asfarray(eval('df2.Det1_' + elem)) + np.asfarray(eval('df2.Det3_' + elem))
    hdr=db[scan_id]['start']
    x_motor = hdr['motor']
    x = np.asarray(df2[x_motor])
    xrf[xrf<(np.max(xrf)*threshold)] = 0.
    xrf[xrf>=(np.max(xrf)*threshold)] = 1.
    #print(x)
    #print(xrf)
    mc = find_mass_center_1d(xrf,x)
    print(mc)
    if moveflag:
        if x_motor == 'zpssx':
            if((mc < .2) and movepiezoflag):
                yield from bps.mov(zps.zpssx,mc)
            else:
                yield from bps.movr(zps.smarx,(mc)/1000.)
        if x_motor == 'zpssy':
            if((mc < .2) and movepiezoflag):
                yield from bps.mov(zps.zpssy,mc)
            else:
                yield from bps.movr(zps.smary,(mc)/1000.)
        if x_motor == 'zpssz':
            if((mc < .2) and movepiezoflag):
                yield from bps.mov(zps.zpssz,mc)
            else:
                yield from bps.movr(zps.smarz,(mc)/1000.)
    else:
        if x_motor == 'zpssx':
            print('move smarx by '+np.str(mc/1000.))
        if x_motor == 'zpssy':
            print('move smary by '+np.str(mc/1000.))
    return mc

def mov_to_line_center_mll(scan_id=-1,elem='Au',threshold=0,moveflag=1,movepiezoflag=0):
    h = db[scan_id]
    scan_id  = h.start['scan_id']
    df2 = h.table()
    xrf = np.array(df2['Det2_' + elem]) + np.array(df2['Det1_' + elem]) + np.array(df2['Det3_' + elem])

    x_motor = h.start['motor']
    x = np.array(df2[x_motor])
    xrf[xrf<(np.max(xrf)*threshold)] = 0.
    xrf[xrf>=(np.max(xrf)*threshold)] = 1.
    #print(x)
    #print(xrf)
    mc = find_mass_center_1d(xrf,x)
    print(mc)
    if moveflag:
        if x_motor == 'dssx':
            if(movepiezoflag):
                mov(smlld.dssx,mc)
            else:
                movr(smlld.dsx,-1*mc)
        if x_motor == 'dssy':
            if(movepiezoflag):
                mov(smlld.dssy,mc)
            else:
                movr(smlld.dsy,mc/1000.)
        if x_motor == 'dssz':
            if(movepiezoflag):
                mov(smlld.dssz,mc)
            else:
                movr(smlld.dsz,mc)
    else:
        if x_motor == 'dssx':
            print('move dssx by '+np.str(mc))
        if x_motor == 'dssz':
            print('move dssz by '+np.str(mc))

def mov_to_image_cen_zpss(scan_id=-1, elem='Ni', bitflag=1):

    df2 = db.get_table(db[scan_id],fill=False)
    xrf = np.asfarray(eval('df2.Det2_' + elem)) + np.asfarray(eval('df2.Det1_' + elem)) + np.asfarray(eval('df2.Det3_' + elem))
    #x = np.asarray(df2.zpssx)
    x = np.asarray(df2.zpssz)
    y = np.asarray(df2.zpssy)
    I0 = np.asfarray(df2.sclr1_ch4)

    scan_info=db[scan_id]
    tmp = scan_info['start']
    nx=tmp['plan_args']['num1']
    ny=tmp['plan_args']['num2']

    xrf = xrf/I0
    xrf = np.asarray(np.reshape(xrf,(ny,nx)))

    if bitflag:
        xrf[xrf <= 0.25*np.max(xrf)] = 0.
        xrf[xrf > 0.25*np.max(xrf)] = 1.


    b = ndimage.measurements.center_of_mass(xrf)

    iy = int(np.round(b[0]))
    ix = int(np.round(b[1]))
    i_max = ix + iy * nx

    x_cen = x[i_max]
    y_cen = y[i_max]
    #print('move smarx, smary by', x_cen, y_cen)
    print('move zpssz, zpssy to ',x_cen, y_cen)

    #movr(zps.smarx, x_cen*0.001)
    mov(zps.zpssz,x_cen)
    sleep(.1)
    #movr(zps.smary, y_cen*0.001)
    mov(zps.zpssy,y_cen)
    sleep(.1)

def go_to_grid(grid='top'):
    if grid == 'top':
        mov(smlld.dsx,-2335.72)
        mov(smlld.dsz,1720.98)
        mov(smlld.dsy,0.56015)
        mov(smlld.sz,754.948)
    elif grid == 'bottom':
        mov(smlld.dsx,-2275.72)
        mov(smlld.dsz,2075.98)
        mov(smlld.dsy,2.2576)
        mov(smlld.sz,754.948)
    elif grid == 's1':
        mov(smlld.dsx,-2322.611)
        mov(smlld.dsz,1720.96)
        mov(smlld.dsy,0.5928)
        mov(smlld.sz,754.948)
def mll_tracking(dx, dy):
    th = smlld.dsth.position
    if np.abs(th) <= 45:
        movr(smlld.dsx, -dx)
    elif np.abs(th) > 45:
        movr(smlld.dsz, dx)
    movr(smlld.dsy, dy/1000.0)


def beep(rp=3):
    b = lambda x: os.system("echo -n '\a'; sleep 0.2;" * x)
    b(rp)

def scale_fly2d(x_start,x_end,x_num,y_start,y_end,y_num,exp):
    angle = smlld.dsth.position
    angle_rad = np.abs(angle * 3.14 / 180.)

    if np.abs(angle) <= 45.:
        x_start_new = x_start / np.cos(angle_rad)
        x_end_new = x_end / np.cos(angle_rad)

        print(angle,' deg', 'scan dssx', 'x scan range: ', x_start_new, '--', x_end_new)
        RE(fly2d(smlld.dssx,x_start_new,x_end_new,x_num,smlld.dssy,y_start,y_end,y_num,exp))
        beep()

    else:
        x_start_new = x_start / np.sin(angle_rad)
        x_end_new = x_end / np.sin(angle_rad)

        print(angle,' deg','scan dssz', 'x scan range: ', x_start_new, '--', x_end_new)
        RE(fly2d(smlld.dssz,x_start_new,x_end_new,x_num, smlld.dssy, y_start, y_end, y_num, exp))
        beep()


def extract_mll_scan_pos(scan_id):
    data = db.get_table(db[scan_id], stream_name='baseline')
    dsx_pos = data.dsx[1]
    dsy_pos = data.dsy[1]
    dsz_pos = data.dsz[1]
    dsth_pos = data.dsth[1]
    sbx_pos = data.sbx[1]
    sbz_pos = data.sbz[1]
    dssx_pos = data.dssx[1]
    dssy_pos = data.dssy[1]
    dssz_pos = data.dssz[1]
    #fdet1_x = data.fdet1_x[1]
    #print(ssx,ssy,ssz)

    print('scan '+np.str(scan_id))
    print('dsx:',dsx_pos, ', dsy:',dsy_pos, ', dsz:',dsz_pos,', dsth:',dsth_pos)
    print('sbx:',sbx_pos, ', sbz:',sbz_pos)
    print('dssx:',dssx_pos,', dssy:',dssy_pos,', dssz:',dssz_pos)

    return {
        smlld.dsz: dsz_pos,
        smlld.dsx: dsx_pos,
        smlld.dsy: dsy_pos,
        smlld.dsth: dsth_pos,
        smlld.dssx: dssx_pos,
        smlld.dssy: dssy_pos,
        smlld.dssz: dssz_pos,
        smlld.sbx: sbx_pos,
        smlld.sbz: sbz_pos}


def recover_mll_scan_pos_plan(scan_id, base_moveflag=True):
    coarse_motors = [smlld.dsz, smlld.dsx, smlld.dsy, smlld.dsth]
    piezo_motors = [smlld.dssx, smlld.dssy, smlld.dssz]
    base_motors = [smlld.sbx, smlld.sbz]

    targets = extract_mll_scan_pos(scan_id)
    cur_postions = {}
    for m in coarse_motors + piezo_motors + base_motors:
        cur_pos[m] = (yield from bp.read(m))

    grp_name = 'recover_moves'

    for m in coarse_motors + piezo_motors:
        yield from bp.abs_set(m, targets[m], group=grp_name)
    if base_moveflag:
        for m in base_motors:
            yield from bp.abs_set(m, targets[m], group=grp_name)
    yield from bp.wait(grp_name)

    return cur_pos

def recover_mll_scan_pos(scan_id,moveflag=True,base_moveflag=True,det_moveflag=False):
    data = db.get_table(db[scan_id], stream_name='baseline')
    dsx_pos = data.dsx[1]
    dsy_pos = data.dsy[1]
    dsz_pos = data.dsz[1]
    dsth_pos = data.dsth[1]
    sbx_pos = data.sbx[1]
    sbz_pos = data.sbz[1]
    dssx_pos = data.dssx[1]
    dssy_pos = data.dssy[1]
    dssz_pos = data.dssz[1]
    #fdet1_x = data.fdet1_x[1]
    #print(ssx,ssy,ssz)

    print('scan '+np.str(scan_id))
    print('dsx:',dsx_pos, ', dsy:',dsy_pos, ', dsz:',dsz_pos,', dsth:',dsth_pos)
    print('sbx:',sbx_pos, ', sbz:',sbz_pos)
    print('dssx:',dssx_pos,', dssy:',dssy_pos,', dssz:',dssz_pos)

    if moveflag:
        #if det_moveflag:
        #    mov(fdet1.x,fdet1_x)
        #    print('moving flourescence det, wait 5 sec ...')
        #    sleep(5)
        yield from bps.mov(smlld.dsz,dsz_pos)
        yield from bps.mov(smlld.dsx,dsx_pos)
        yield from bps.mov(smlld.dsy,dsy_pos)
        yield from bps.mov(smlld.dsth,dsth_pos)
        yield from bps.mov(smlld.dssx,dssx_pos)
        yield from bps.mov(smlld.dssy,dssy_pos)
        yield from bps.mov(smlld.dssz,dssz_pos)
        if base_moveflag:
            yield from bps.mov(smlld.sbx,sbx_pos)
            yield from bps.mov(smlld.sbz,sbz_pos)

def recover_zp_scan_pos(scan_id,zp_move_flag=0,smar_move_flag=0):
    data = db.get_table(db[scan_id],stream_name='baseline')
    bragg = data.dcm_th[1]
    zpz1 = data.zpz1[1]
    zpx = data.zpx[1]
    zpy = data.zpy[1]
    smarx = data.smarx[1]
    smary = data.smary[1]
    smarz = data.smarz[1]
    ssx = data.zpssx[1]
    ssy = data.zpssy[1]
    ssz = data.zpssz[1]
    zpsz = data.zpsz[1]
    #print(ssx,ssy,ssz)

    print('scan '+np.str(scan_id))
    print('dcm_th:'+np.str(bragg))
    #print('zpz1: '+np.str(zpz1)+', zpx:'+np.str(zpx)+', zpy:'+np.str(zpy))
    print('zpz1:', np.str(zpz1))
    print('zpsz:', np.str(zpsz))
    print('smarx:'+np.str(smarx)+', smary:'+np.str(smary)+', smarz:'+np.str(smarz))
    print('zpssx:'+np.str(ssx)+', zpssy:'+np.str(ssy)+', zpssz:'+np.str(ssz))

    if zp_move_flag:
        #yield from bps.mov(dcm.th,bragg)
        yield from bps.mov(zp.zpz1,zpz1)
        yield from bps.mov(zp.zpx,zpx)
        yield from bps.mov(zp.zpy,zpy)

    if smar_move_flag:
        #mov(dcm.th,bragg)
        yield from bps.mov(zps.smarx,smarx)
        yield from bps.mov(zps.smary,smary)
        yield from bps.mov(zps.smarz,smarz)
        yield from bps.mov(zps.zpssx,ssx)
        yield from bps.mov(zps.zpssy,ssy)
        yield from bps.mov(zps.zpssz,ssz)



def export_merlin(sid,num=1):
    for i in range(num):
        sid, df = _load_scan(sid, fill_events=False)
        path = os.path.join('/data/users/2019Q1/Robinson_2019Q1/raw_data/', 'scan_{}.txt'.format(sid))
        print('Scan {}. Saving to {}'.format(sid, path))
        #non_objects = [name for name, col in df.iteritems() if col.dtype.name not in ('object', )]
        #dump all data
        non_objects = [name for name, col in df.iteritems()]
        df.to_csv(path, float_format='%1.5e', sep='\t',
                  columns=sorted(non_objects))

        path = os.path.join('/data/users/2019Q1/Robinson_2019Q1/raw_data/', 'scan_{}_scaler.txt'.format(sid))
        #np.savetxt(path, (df['sclr1_ch3'], df['p_ssx'], df['p_ssy']), fmt='%1.5e')
        #np.savetxt(path, (df['sclr1_ch4'], df['zpssx'], df['zpssy']), fmt='%1.5e')
        filename = get_all_filenames(sid,'merlin1')
        num_subscan = len(filename)
        if num_subscan == 1:
            for fn in filename:
                break
            path = os.path.join('/data/users/2019Q1/Robinson_2019Q1/raw_data/', 'scan_{}.h5'.format(sid))
            mycmd = ''.join(['scp', ' ', fn, ' ', path])
            os.system(mycmd)
        else:
            h = db[sid]
            images = db.get_images(h,name='merlin1')
            path = os.path.join('/data/users/2019Q1/Robinson_2019Q1/raw_data/', 'scan_{}.h5'.format(sid))
            f = h5py.File(path, 'w')
            dset = f.create_dataset('/entry/instrument/detector/data', data=images)
            f.close()
            '''''
            j = 1
            for fn in filename:
                path = os.path.join('/home/hyan/export/', 'scan_{}_{}.h5'.format(sid, j))
                mycmd = ''.join(['scp', ' ', fn, ' ', path])
                os.system(mycmd)
                j = j + 1
            '''''
        sid = sid + 1

def position_scan(dsx_list,dsy_list,x_range_list,x_num_list,y_range_list,y_num_list,exp_list):
    x_list = np.array(dsx_list)
    y_list = np.array(dsy_list)
    x_range_list = np.array(x_range_list)
    y_range_list = np.array(y_range_list)
    x_num_list = np.array(x_num_list)
    y_num_list = np.array(y_num_list)
    exp_list = np.array(exp_list)

    dsx_0 = smlld.dsx.position
    dsy_0 = smlld.dsy.position
    num_scan = np.size(x_list)
    #mov(ssa2.hgap,0.03)
    #mov(ssa2.vgap,0.02)
    for i in range(num_scan):
        print('move to position ',i+1,'/',num_scan)
        mov(smlld.dsx,x_list[i])
        mov(smlld.dsy,y_list[i])
        RE(fly2d(smlld.dssx,-x_range_list[i]/2,x_range_list[i]/2,x_num_list[i]/1,smlld.dssy,-y_range_list[i]/2,y_range_list[i]/2,y_num_list[i]/1,exp_list[i]/1))
        #plot2dfly(-1,'Er_L')
        #printfig()
        print('wait 0.2 sec...')
        sleep(0.2)

    mov(smlld.dsx,dsx_0)
    mov(smlld.dsy,dsy_0)
    #mov(ssa2.hgap,0.15)
    #mov(ssa2.vgap,0.05)



def tt_scan():
    yield from recover_zp_scan_pos(42343,1,1)
    yield from fly2d(dets1,zpssx, -10, 10, 250, zpssy, -10, 10, 250, 0.05)
    yield from recover_zp_scan_pos(42336,1,1)
    yield from fly2d(dets1,zpssx, -10, 10, 250, zpssy, -10, 10, 250, 0.05)
    yield from recover_zp_scan_pos(42331,1,1)
    yield from fly2d(dets1,zpssx, -10, 10, 250, zpssy, -10, 10, 250, 0.05)
    yield from recover_zp_scan_pos(42311,1,1)
    yield from fly2d(dets1,zpssx, -10, 10, 250, zpssy, -10, 10, 250, 0.05)
    yield from recover_zp_scan_pos(42312,1,1)
    yield from fly2d(dets1,zpssx, -10, 10, 250, zpssy, -10, 10, 250, 0.05)
    yield from recover_zp_scan_pos(42321,1,1)
    yield from fly2d(dets1,zpssx, -10, 10, 250, zpssy, -10, 10, 250, 0.05)


def movr_mll_sbz(d):
    print(d,0.01*d,-0.01*d)
    yield from bps.movr(sbz,d)
    yield from bps.movr(dsx,0.01*d)
    yield from bps.movr(dsy,-0.01*d)




# ========================================================================================================================

def return_line_center_img_sum(sid,threshold=0.3):

    Result = plot_img_sum_for_centering(sid, det = 'merlin1', roi_flag=False,x_cen=0,y_cen=0,size=0)

    xrf = Result['tot']
    #threshold = np.max(xrf)/10.0
    x = Result['x']

    #xrf = xrf * -1
    #xrf = xrf - np.min(xrf)

    #print(x)
    #print(xrf)
    xrf[xrf<(np.max(xrf)*threshold)] = 0.
    #index = np.where(xrf == 0.)
    #xrf[:index[0][0]] = 0.
    #xrf[xrf>=(np.max(xrf)*threshold)] = 1.
    mc = find_mass_center_1d(xrf,x)
    return mc


def plot_img_sum_for_centering(sid, det = 'merlin1', roi_flag=False,x_cen=0,y_cen=0,size=0):
    h = db[sid]
    sid = h.start['scan_id']
    imgs = list(h.data(det))
    #imgs = np.array(imgs)
    imgs = np.array(np.squeeze(imgs))
    df = h.table()
    mon = np.array(df['sclr1_ch4'],dtype=float32)
    #plt.figure()
    #plt.imshow(imgs[0],clim=[0,50])
    if roi_flag:
        imgs = imgs[:,x_cen-size//2:x_cen+size//2,y_cen-size//2:y_cen+size//2]
    mots = h.start['motors']
    num_mots = len(mots)
    #num_mots = 1
    #df = h.table()
    x = df[mots[0]]
    x = np.array(x)
    tot = np.sum(imgs,2)
    tot = np.array(np.sum(tot,1), dtype=float32)
    tot = np.divide(tot,mon)

    return {'x':x,'tot':tot}


def zp_theta_scan_center_angle(angle_start,angle_end,angle_step_size,x1,x2,x_num,y1,y2,y_num):
    #p_v_ry_0 = p_v_ry.position
    #p_vx_0 = p_vx.position
    #p_vy_0 = p_vy.position
    zpsth_0 = zpsth.position
    angle_step_num = int((angle_end - angle_start) / angle_step_size) + 1
    print(angle_start,angle_end,angle_step_size,angle_step_num)
    yield from bps.mov(zpsth,angle_start)
    lc_angle = zpsth_0

    for i in range(int(angle_step_num)):
        while (sclr2_ch4.get() < 50000):
            yield from bps.sleep(60)
            print('IC3 is lower than 50000, waiting...')

        #print('running scan at ',zpsth.position)
        print('Start the scan at %d step ' %(i))

        yield from fly1d(dets1,zpssx,-10,10,100,0.1)
        lc = return_line_center(-1,'Co')
        print('zpssx center is %.3f' %(lc))
        yield from bps.mov(zpssx,lc)
        xspress3.unstage()

        yield from fly1d(dets1,zpssy,-10,10,100,0.1)
        lc = return_line_center(-1,'Co')
        print('zpssy center is %.3f' %(lc))
        yield from bps.mov(zpssy,lc)
        xspress3.unstage()

        if np.remainder(i, 50) == 0:
            yield from bps.mov(zpsth, lc_angle)
            yield from dscan(dets1,zpsth,-0.5,0.5,20,0.1)
            lc_angle = return_line_center_img_sum(-1)

        print('zpsth center is %.3f' %(lc_angle))
        print('current scan is at angle %.3f' %(lc_angle - zpsth_0 + angle_start + i*angle_step_size))
        yield from bps.mov(zpsth, lc_angle - zpsth_0 + angle_start + i*angle_step_size)
        xspress3.unstage()


        yield from fly2d(dets1, zpssx,x1,x2,x_num, zpssy, y1, y2,y_num, 0.05, return_speed = 40)

        #yield from mesh(dets1,zpssy,-0.3,0.3,20,zpssx,-0.3,0.3,20,10)
        #yield from bps.movr(zpsth, angle_step_size)

        #curr_angle = p_v_ry.position
        #corr_p_vx = (curr_angle)**2*4.126e-10+curr_angle*0.0001108+0.002298
        #print (corr_p_vx,curr_angle)
        #yield from bps.mov(p_vx,corr_p_vx)
        #yield from bps.movr(p_vy,0.0004)

        merlin1.unstage()
        xspress3.unstage()
        print('waiting for 2 sec...')
        yield from bps.sleep(2)


    #yield from bps.mov(p_v_ry,p_v_ry_0)
    #yield from bps.mov(p_vx,p_vx_0)
    #yield from bps.mov(p_vy, p_vy_0)
    yield from bps.mov(zpsth,zpsth_0)


# ========================================================================================================================


import epics
def zp_rock(angle_start,angle_end,x_step, num):
    p_v_ry_0 = p_v_ry.position
    p_v_rx_0 = p_v_rx.position
    p_vx_0 = p_vx.position
    p_vy_0 = p_vy.position
    angle_step = (angle_end - angle_start) / num
    #x_step = (xe - xs) / num
    yield from bps.movr(p_v_ry, angle_start)
    yield from bps.movr(p_vx,-x_step*num/2)
    print(angle_start,angle_end,angle_step,num)
    for i in range(int(num+1)):
        caput('XF:03IDC-ES{Merlin:2}TIFF1:Capture',1)
        #print('running scan at ',p_v_ry.position)
        #yield from fly2d(dets2, ssx,-1,1,200, ssy, -1, 1, 200, 0.05, return_speed = 40)
        yield from bps.movr(p_v_ry, angle_step)
        yield from bps.movr(p_vx,x_step)
        merlin2.unstage()
        xspress3.unstage()
        print('waiting for 2 sec...')
        yield from bps.sleep(2)


    yield from bps.mov(p_v_ry,p_v_ry_0)
    yield from bps.mov(p_vx,p_vx_0)
    yield from bps.mov(p_v_rx,p_v_rx_0)
    yield from bps.mov(p_vy,p_vy_0)

def peak_with_voltage(start,end,n_steps, pv_name = "XF:03ID-BI{EM:BPM1}DAC0"):

    shutter_b_cls_status = caget('XF:03IDB-PPS{PSh}Sts:Cls-Sts')
    shutter_c_status = caget('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0')

    if shutter_b_cls_status == 0:

        dcm_pitch_volt = caget(pv_name)
        x = np.linspace(dcm_pitch_volt+start,dcm_pitch_volt+end,n_steps+1)
        y = np.arange(n_steps+1)

        for i in tqdm.tqdm(range(n_steps+1),desc = 'peaking flux'):
            
            caput(pv_name,x[i])
            yield from bps.sleep(4)
            if shutter_c_status == 0:
                y[i] = sclr2_ch2.get()
            else:
                y[i] = sclr2_ch4.get()
        
        peak = x[y == np.max(y)]

        yield from bps.sleep(3)
        caput(pv_name,peak[0])
        yield from bps.sleep(3)

    else:
        print('Shutter B is Closed')
        return


def peak_xy_volt(iter = 2):

    for i in tqdm.tqdm(range(iter)):
        yield from peak_with_voltage(-0.05,0.05,10, pv_name = "XF:03ID-BI{EM:BPM1}DAC0")
        yield from peak_with_voltage(-0.05,0.05,10, pv_name = "XF:03ID-BI{EM:BPM1}DAC1")
    

def peak_bpm_x(start,end,n_steps):
    shutter_b_cls_status = caget('XF:03IDB-PPS{PSh}Sts:Cls-Sts')
    shutter_c_status = caget('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0')

    if shutter_b_cls_status == 0:

        caput('XF:03IDC-ES{Status}ScanRunning-I', 1)
        bpm_y_0 = caget('XF:03ID-BI{EM:BPM1}fast_pidX.VAL')
        x = np.linspace(bpm_y_0+start,bpm_y_0+end,n_steps+1)
        y = np.arange(n_steps+1)
        #print(x)
        for i in range(n_steps+1):
            caput('XF:03ID-BI{EM:BPM1}fast_pidX.VAL',x[i])
            if i == 0:
                yield from bps.sleep(8)
            else:
                yield from bps.sleep(5)

            if shutter_c_status == 0:
                y[i] = sclr2_ch2.get()
            else:
                y[i] = sclr2_ch4.get()
        peak = x[y == np.max(y)]

        plt.figure()
        plt.plot(x,y)
        #plt.hold(2)
        #plt.close()

        #print(peak)
        caput('XF:03ID-BI{EM:BPM1}fast_pidX.VAL',peak[0])
        yield from bps.sleep(5)

        xbpmc_x = caget('XF:03ID-BI{EM:BPM2}PosX:MeanValue_RBV')
        xbpmc_y = caget('XF:03ID-BI{EM:BPM2}PosY:MeanValue_RBV')
        print(xbpmc_x,xbpmc_y)
        caput('XF:03IDC-CT{FbPid:03}PID.VAL',xbpmc_y)
        caput('XF:03IDC-CT{FbPid:04}PID.VAL',xbpmc_x)
        caput('XF:03IDC-ES{Status}ScanRunning-I', 0)


    else:
        print('Shutter B is Closed')

    #plt.pause(5)
    #plt.close()

def peak_bpm_y(start,end,n_steps):
    shutter_b_cls_status = caget('XF:03IDB-PPS{PSh}Sts:Cls-Sts')
    shutter_c_status = caget('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0')


    if shutter_b_cls_status == 0:

        caput('XF:03IDC-ES{Status}ScanRunning-I', 1)
        bpm_y_0 = caget('XF:03ID-BI{EM:BPM1}fast_pidY.VAL')
        x = np.linspace(bpm_y_0+start,bpm_y_0+end,n_steps+1)
        y = np.arange(n_steps+1)
        #print(x)
        for i in range(n_steps+1):
            caput('XF:03ID-BI{EM:BPM1}fast_pidY.VAL',x[i])
            if i == 0:
                yield from bps.sleep(5)
            else:
                yield from bps.sleep(2)

            if shutter_c_status == 0:
                y[i] = sclr2_ch2.get()

            else:
                y[i] = sclr2_ch4.get()


        peak = x[y == np.max(y)]
        plt.figure()
        plt.plot(x,y)
        #plt.hold(2)
        plt.close()
        #print(peak)
        caput('XF:03ID-BI{EM:BPM1}fast_pidY.VAL',peak[0])
        yield from bps.sleep(2)

        xbpmc_x = caget('XF:03ID-BI{EM:BPM2}PosX:MeanValue_RBV')
        xbpmc_y = caget('XF:03ID-BI{EM:BPM2}PosY:MeanValue_RBV')
        print(xbpmc_x,xbpmc_y)
        caput('XF:03IDC-CT{FbPid:03}PID.VAL',xbpmc_y)
        caput('XF:03IDC-CT{FbPid:04}PID.VAL',xbpmc_x)
        caput('XF:03IDC-ES{Status}ScanRunning-I', 0)


    else:
        print('Shutter B is Closed')

    #plt.pause(5)
    #plt.close()

def peak_all(x_start = -25,x_end=25,x_n_step=50, y_start = -15,y_end=15, y_n_step=30):

	peak_bpm_y(y_start,y_end,y_n_step)
	peak_bpm_x(x_start,x_end,x_n_step)
	peak_bpm_y(y_start,y_end,y_n_step)


def recover_and_scan(sid, dets, mot1, mot1_s, mot1_e, mot1_n, mot2, mot2_s, mot2_e, mot2_n, exp_t, moveZP = False):

    yield from recover_zp_scan_pos(int(sid),moveZP,1)
    yield from bps.sleep(3)
    yield from check_for_beam_dump(threshold = 5000)
    yield from fly2d(dets, mot1, mot1_s, mot1_e, mot1_n, mot2, mot2_s, mot2_e, mot2_n, exp_t)
    yield from bps.sleep(3)
    yield from bps.mov(zpssx,0,zpssy,0)
    yield from bps.sleep(3)
    


def insert_xrf_map_to_pdf(scan_id = -1, elements = ["Cr", "Fe"],
                          title_ = ['energy','zpsth'], 
                          norm = 'sclr1_ch4'):

    """
        insert 2D-XRF maps to the pdf log from a single scan
        Paramaters
            
            - scan_id; relayive or absolute numbers eg: -1, 190543
            - elements; list of elements eg:["Cr", "Ti"]
            - title_; multiple titles can be added to the figure. eg: ["energy", "zpsth"], ["dsth"]
            - norm; (optional) specify IC normaization. default is 'sclr1_ch4'; None ignores normalization
            - a time stamp will be added to the bottom of the figure

    """

    with suppress(Exception):

        h = db[int(scan_id)]
        df = h.table()
        dim1,dim2 = h.start['num1'], h.start['num2']

        tot = len(elements)

        if tot ==1:
            cols = 1

        else:
            cols = 2


        Rows = tot // cols 
        
        
        if tot % cols != 0:
            Rows += 1
        
        
        Position = range(1,tot + 1)

        fig = plt.figure()
        fig.suptitle("scan_id = "+ str(h.start["scan_id"]), size = 'xx-large')

        for n, elem in enumerate(elements):
        
            if elem in df:
                det = df[elem]
            else:
                det = ( df[f'Det1_{elem}'] +
                        df[f'Det1_{elem}'] +
                        df[f'Det1_{elem}'] ). to_numpy()

            if norm == None:
                mon = np.ones_like(det)
            
            else:

                mon = df[norm].to_numpy()
                mon[mon == 0] = mon.mean()
            
            norm_data = np.float32(det/mon)

            ax = fig.add_subplot(Rows,cols,Position[n])
            im = ax.imshow(np.float32(norm_data.reshape(dim2,dim1)))
            ax.set_title(elem)
            divider = make_axes_locatable(ax)
            cax = divider.append_axes('right', size='5%', pad=0.05)
            fig.colorbar(im, cax=cax, orientation='vertical')
            fig.tight_layout()


        time_str = "scan date & time = " + df["time"].iloc[-1].strftime('%Y-%m-%d %X')

        titleValue1 = (h.table("baseline")[title_[0]].values)[0]
        titleValue2 = (h.table("baseline")[title_[1]].values)[0]

        title_str = f"{title_[0]} = {titleValue1:.4f} , {title_[1]} = {titleValue2:.4f}"

        #insertFig(note = time_str, title = '= {:.4f}'.format(check_baseline(scan,title_)) )
        insertFig(note = time_str, title = title_str)

        plt.close()


def insert_xrf_series_to_pdf(startSid,endSid, elements = ["Cr", "Ti"], figTitle = ["energy","zpsth"],
                             mon = 'sclr1_ch4', diffSum = False):

    """ insert 2D-XRF maps to the pdf log from a series of scan.
        - elements has to be in the list. eg:["Cr", "Ti"]
        - a title can be added to the figure. Commonly: "enegry", "zpsth", "dsth"
        - a time stamp will be added to the bottom of the figure

        """

    scan_nums = np.arange(startSid,endSid+1)
    for i in scan_nums:
        if len(db[int(i)].start['motors']) == 2:
            print(f"{i} = 2D scan")

            if diffSum:
                insert_diffSum_to_pdf(scan = int(i),det = "merlin1", thMotor = "zpsth")
            else:
                insert_xrf_map_to_pdf(int(i),elements,figTitle, norm=mon)

    save_page()

def insert_diffSum_to_pdf(scan = -1,det = "merlin1", thMotor = "zpsth"):

    plot_img_sum(scan, det, threshold=[0,200000])
    time_str = str((db[int(scan)].table("baseline")['time'].values)[-1])
    titleValue = (db[int(scan)].table("baseline")[thMotor].values)[0]
    insertFig(note = time_str, title = f"{thMotor} = {titleValue :.4f}" )
    plt.close()

def plot_data(sid = -1,  elem = 'Pt_L', mon = 'sclr1_ch4'):

    h = db[sid]
    mots = h.start['motors']

    if len(mots) == 1:

        plot(sid,elem, mon)

    if len(mots) == 2:

        plot2dfly(sid, elem,  mon)


def mosaic_overlap_scan(dets = None, ylen = 100, xlen = 100, overlap_per = 15, dwell = 0.05, 
                        step_size = 500, plot_elem = ["Cu","Fe","Ba_L","Ti"],mll = False):

    """mosiac scan with 5 um overlap ; 
    xlen and ylen should be multiple of 25"""

    if dets is None:
        dets = dets_fs

    max_travel = 30
        
    dsx_i = dsx.position
    dsy_i = dsy.position

    smarx_i = smarx.position
    smary_i = smary.position

    scan_dim = max_travel - round(max_travel*overlap_per*0.01)

    x_tile = round(xlen/scan_dim)
    y_tile = round(ylen/scan_dim)

    xlen_updated = scan_dim*x_tile
    ylen_updated = scan_dim*y_tile


    X_position = np.linspace(0,xlen_updated-scan_dim,x_tile)
    Y_position = np.linspace(0,ylen_updated-scan_dim,y_tile)

    num_steps = round(max_travel*1000/step_size)
    
    unit = "minutes"
    fly_time = (num_steps**2)*dwell*2
    num_flys= len(X_position)*len(Y_position)
    total_time = (fly_time*num_flys)/60
    

    if total_time>60:
        total_time/=60
        unit = "hours"

    #print(f'total time = {total_time} {unit}; 10 seconds to quit')

    ask = input(f"Optimized scan x and y range = {xlen_updated} by {ylen_updated};"
     f"\n total time = {total_time} {unit}"
     f"\n Do you wish to continue? (y/n) ")

    if ask == 'y':

        #yield from bps.sleep(10)
        first_sid = db[-1].start["scan_id"]+1

        if mll:

            yield from bps.movr(dsy, ylen_updated/-2)
            yield from bps.movr(dsx, xlen_updated/-2)

        else:
            yield from bps.movr(smary, ylen_updated*-0.001/2)
            yield from bps.movr(smarx, xlen_updated*-0.001/2)

        
        for i in tqdm.tqdm(Y_position):
                for j in tqdm.tqdm(X_position):
                    print((i,j))
                    yield from check_for_beam_dump(threshold=5000)
                    yield from bps.sleep(1) #cbm catchup time

                    if mll:

                        yield from bps.movr(dsy, i)
                        yield from bps.movr(dsx, j)
                        yield from fly2d(dets,dssx,-15,15,num_steps,dssy,-15,15,num_steps,dwell)
                        yield from bps.sleep(3)
                        yield from bps.mov(dssx,0,dssy,0)
                        insert_xrf_map_to_pdf(-1,plot_elem,'dsx')
                        yield from bps.mov(dsx, dsx_i)
                        yield from bps.mov(dsy,dsy_i)

                    else:

                        yield from bps.movr(smary, i*0.001)
                        yield from bps.movr(smarx, j*0.001)
                        yield from fly2d(dets, zpssx,-15,15,num_steps,zpssy, -15,15,num_steps,dwell)
                        yield from bps.sleep(1)
                        yield from bps.mov(zpssx,0,zpssy,0)
                        '''
                        try:
                            insert_xrf_map_to_pdf(-1,plot_elem,'smarx')
                        except:
                            plt.close()
                            pass
                        '''

                        yield from bps.mov(smarx, smarx_i)
                        yield from bps.mov(smary,smary_i) 

        save_page()                 
        '''
        plot_mosiac_overlap(grid_shape = (y_tile,x_tile), 
                            first_scan_num = int(first_sid),
                            elem = plot_elem[0], 
                            show_scan_num = True)
        '''
    else:
        return 


def plot_mosiac_overlap(grid_shape = (4,4), first_scan_num = -8, 
                        elem = "Fe", show_scan_num = True):
    
    fig, axs = plt.subplots(grid_shape[0],grid_shape[1])
    fig.subplots_adjust(hspace = 0, wspace = -0.57)
    fig.suptitle(elem)
    axs = axs.ravel()

    for i in range(int(grid_shape[0]*grid_shape[1])):
        sid = i+first_scan_num
        print(sid)

        h = db[int(sid)]
        df = h.table()
        dim1,dim2 = h.start['num1'], h.start['num2']

    

        if elem in df:
            det = df[elem]
        else:
            det = ( df[f'Det1_{elem}'] +
                    df[f'Det1_{elem}'] +
                    df[f'Det1_{elem}'] ). to_numpy()

        mon = df["sclr1_ch4"].to_numpy()
        mon[mon == 0] = mon.mean()
        norm_data = (det/mon)

        axs[i].imshow(np.float32(norm_data.reshape(dim1,dim2)))
        if show_scan_num:
            axs[i].set_title(
                            str(h.start["scan_id"]), y=1.0, pad=-14,
                            fontdict = {
                                        'color':'r',
                                        'fontsize':8,
                                        }
                            )
        axs[i].set_xticklabels([])
        axs[i].set_yticklabels([])
        axs[i].set_xticks([])
        axs[i].set_yticks([])


