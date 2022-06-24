#Last Update 09/11/2021 by AP

"""

ReadMe:

The workflow for xanes experiment is define below. This macro aims to use one flow for XANES of any given element.
This macro is designed to work with the GUI inputs as well.
To add a new element add the paramer file in the format given below


EXAMPLE OF USAGE:


For XANES Scan: <zp_list_xanes2d(FeXANES,dets1,zpssx,-13,11,150,zpssy,-13,11,150,0.05,
                    xcen = 0, ycen = 0,doAlignScan = False, alignElem = 'Fe',
                    alignX = (-1,1,100,0.1),
                    alignY = (-1,1,100,0.1), pdfElem = ['Fe','Cr'],
                    saveLogFolder = '/data/users/2021Q3/Ajith_2021Q3')


For Foil Calibration: <zp_list_xanes2d(e_list,dets6,mot1,x_s,x_e,x_num,mot2,y_s,y_e,y_num,accq_t,
                    xcen = 0, ycen = 0, doAlignScan = False, pdfLog = False,
                    foilCalibScan = True, peakBeam = False)

"""


import numpy as np
from datetime import datetime
import pandas as pd

import scipy.constants as consts


#Paramer list from previous runs in the order of atomic number of the element

CrXANES = {'high_e':6.0, 'high_e_zpz1':10.48, 'zpz1_slope':-5.04,
          'energy':[(5.97,5.98,0.005),(5.981,6.03,0.001), (6.032,6.046,0.005)] }
          
MnXANES = {'high_e':6.6, 'high_e_zpz1':68.3165, 'zpz1_slope':-5.04,
          'energy':[(6.520,6.530,0.005),(6.531,6.580,0.001),(6.585,6.601,0.005)]}
               
FeXANES = {'high_e':7.2, 'high_e_zpz1':5.235, 'zpz1_slope':-5.04,
          'energy':[(7.08,7.10,0.005),(7.101,7.140,0.001),(7.144, 7.2, 0.004)],}

NiXANES = {'high_e':8.427, 'high_e_zpz1':58.32, 'zpz1_slope':-5.04,
          'energy':[(8.30,8.32,0.005),(8.321,8.38,0.001),(8.382,8.430,0.005)],}

CuXANES = {'high_e':9.06,  'high_e_zpz1':-4.905, 'zpz1_slope':-5.04,
          'energy':[(8.96,8.975,0.005),(8.976,9.003,0.001)],}

ZnXANES =  {'high_e':9.7, 'high_e_zpz1':50.87, 'zpz1_slope':-5.04,
          'energy':[(9.64,9.666,0.005),(9.6665,9.681,.0005),(9.682,9.701,0.002),(9.705,9.725,0.005)]}

HfXANES =  {'high_e':9.6, 'high_e_zpz1':-7.775, 'zpz1_slope':-5.04,
          'energy':[(9.500,9.540,0.005),(9.541,9.6,0.001)]}

LuL3XANES =  {'high_e':9.3, 'high_e_zpz1':-5.4246, 'zpz1_slope':-5.04,
          'energy':[(9.150,9.200,0.005),(9.201,9.350,0.001),(9.352,9.400,0.002)]}


"""
PreAs = np.linspace(11845,11860,6)
As_XANES = np.linspace(11861,11885,49)
PostAs = np.linspace(11886,11901,6)

"""

                                ######################################
                                ######### FUNCTIONS BELOW ############
                                ######################################


def peak_the_flux():

    """ Scan the c-bpm set points to find IC3 maximum """

    print("IC3is below threshold; Peaking the beam.")
    yield from bps.sleep(2)
    yield from peak_bpm_y(-5,5,10)
    yield from bps.sleep(1)
    yield from peak_bpm_x(-15,15,6)
    yield from bps.sleep(1)
    yield from peak_bpm_y(-2,2,4)
    

def move_energy(e,zpz_ ):
    yield from bps.sleep(1)

    #tuning the scanning pv on to dispable c bpms
    caput('XF:03IDC-ES{Status}ScanRunning-I', 1)

    yield from Energy.move(e, moveMonoPitch=False, moveMirror = "ignore")
    yield from mov_zpz1(zpz_)
    yield from bps.sleep(4)



def generateEPoints(ePointsGen = [(9.645,9.665,0.005),(9.666,9.7,0.0006),(9.705,9.725,0.005)],reversed = True):

    """

    Generates a list of energy values from the given list

    input: Tuples in the format (start energy, end energy, energy resolution),
    if reversed is true the list will be transposed

    return : list of energy points

    """

    e_points = []

    if isinstance(ePointsGen[0], tuple):

        for values in ePointsGen:
            #use np.arange to generate values and extend it to the e_points list
            e_points.extend(np.arange(values[0],values[1],values[2]))

    elif isinstance(ePointsGen, list):
        e_points = ePointsGen

    else:
        raise TypeError("Invalid energy format")

    if reversed:
        #retrun list in the reversted order
        return e_points[::-1]
    else:
        return e_points

def generateEList(XANESParam = CrXANES, highEStart = True):

    """

    Generates a pandas dataframe of optics motor positions. Function uses high E and low E values in the dictionary
    to generate motor positions for all the energy points, assuming linear relationship.

    input: Dictionary conating optics values at 2 positions (high E and low E), option to start from high E or low E

    return : Dataframe looks like below;

       energy    ugap  crl_theta  ZP focus
    0   7.175  7652.5       1.75   65.6575
    1   7.170  7648.0       1.30   65.6870
    2   7.165  7643.5       0.85   65.7165
    3   7.160  7639.0       0.40   65.7460
    4   7.155  7634.5      -0.05   65.7755

    """
    # empty dataframe
    e_list = pd.DataFrame()

    #add list of energy as first column to DF
    e_list['energy'] = generateEPoints (ePointsGen = XANESParam ['energy'], reversed = highEStart)

    #read the paramer dictionary and calculate ugap list
    high_e = XANESParam['high_e']

    #zone plate increament is very close to the theorticla value , same step as above for zp focus
    zpz1_ref, zpz1_slope = XANESParam['high_e_zpz1'],XANESParam['zpz1_slope']
    zpz1_list = zpz1_ref + (e_list['energy'] - high_e)*zpz1_slope
    e_list['ZP focus'] = zpz1_list

    #return the dataframe
    return e_list



def zp_list_xanes2d(elemParam,dets,mot1,x_s,x_e,x_num,mot2,y_s,y_e,y_num,accq_t,highEStart = False,
                    doAlignScan = True, alignX = (-2,2,100,0.1,'Fe',0.7, True),
                    alignY = (-2,2,100,0.1,'Fe',0.7, True), 
                    pdfElem = ('Fe','Cr'),doScan = True, moveOptics = True,pdfLog = True, 
                    foilCalibScan = False, peakBeam = True,
                    saveLogFolder = '/home/xf03id/Downloads'):
                    
                    
    """ 
    Function to run XANES Scan. 
    
    Arguments:
           1. elemParam: Dictionary -  containg low and high energy optics positions and other useful info 
           2. dets: list - detector system in use
           3. mot1, mot2: EpicsMotors- Motors used for 2D scanning (eg: zpssx, zpssy, etc)
           4. xs,xe,ys,ye: float - scan start and end positions in X&Y directions
           5. x_num,y_num: float - number of steps in X&Y directions
           6. accq_t: float - aquistion (dwell) time for flyscan
           7. highEStart: boolean - if True start the stack with high energies first (Descenting order)
           8. doAlignScan: boolean - if True registration scans will be performed before the 2D scan
           9. xcen, ycen; positions where alignemnt scan would be done. This number updates after each alignment scan
           10. Options for reginstration scans
           11. Options to save XRFs to pdf after each scan
           12. Options to do foil calibration scans
           13. Save important information in CSV format to selected forlder 
           14. The user can turn on and off alignemnt scans
    
    
    """   
    # marker to track beam dump             
    beamDumpOccured = False
                    
    e_list = generateEList(elemParam, highEStart =  highEStart)

    #add real energy to the dataframe
    e_list['E Readback'] = np.nan 
    
    #add scan id to the dataframe
    e_list['Scan ID'] = np.nan 
    
    #recoed time
    e_list['TimeStamp'] = pd.Timestamp.now()
    
    #Ic values are useful for calibration
    e_list['IC3'] = sclr2_ch4.get() 
    e_list['IC0'] = sclr2_ch2.get()
    e_list['IC3_before_peak'] = sclr2_ch2.get()
    
    
    #record if peak beam happed before the scan   
    e_list['Peak Flux'] = False 
    
    print(e_list.head())
    yield from bps.sleep(10)#time to quit if anything wrong
    
    #get intal ic1 value
    ic_0 = sclr2_ch2.get()
    
    #opening fast shutter for initial ic3 reading
    #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1) 
    yield from bps.sleep(2)
    
    #get the initial ic3 reading for peaking the beam
    ic_3_init =  sclr2_ch4.get()
     
    #close fast shutter after initial ic3 reading
    #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0) 
    
    #remeber the start positions
    zpssz_i = zpssz.position
    zpssy_i = zpssy.position


    for i in range (len(e_list)):

        #if beam dump occur turn the marker on
        if sclr2_ch2.get()<10000:
            beamDumpOccured = True

        #wait if beam dump occured beamdump
        yield from check_for_beam_dump(threshold=10000)
        
        if beamDumpOccured:
            #wait for about 3 minutes for all the feedbacks to kick in
            yield from bps.sleep(200)

            #redo the previous energy
            e_t, zpz_t, *others = e_list.iloc[i-1]

            #turn off the beamdump marker
            beamDumpOccured = False
            
        else:
            #unwrap df row for energy change
            e_t, zpz_t, *others = e_list.iloc[i]
        
        if moveOptics: 
            yield from move_energy(e_t,zpz_t)

        else: pass
        
        #open fast shutter to check if ic3 reading is satistactory
        #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',1) 
        yield from bps.sleep(3)
        
        #get ic3 value before peaking, e change
        ic3_ = sclr2_ch4.get()
        
        # if ic3 value is below the threshold, peak the beam
        if ic3_ < ic_3_init*0.8:
            
            if peakBeam: yield from peak_the_flux()
            fluxPeaked = True # for df record
        else:
            fluxPeaked = False
        
        #for df
        ic_3 = sclr2_ch4.get()
        ic_0 = sclr2_ch2.get()

        # move to particle location for alignemnt scan
        #if doAlignScan:
        
            #yield from bps.mov(zpssx, xcen)
            #yield from bps.mov(zpssy, ycen)
        
        #do the alignemnt scan on the xanes elem after it excited , 
        #otherwise skip or use another element

        if e_list['energy'][i]<0: # for special scans if no align elem available
            
            '''
            yield from fly1d(dets,zpssx,-1,1,100,0.1)
            xcen = return_line_center(-1,'Cl',0.7)
            yield from bps.mov(zpssx, xcen)
            yield from fly1d(dets,zpssy,-1,1 ,100,0.1)
            ycen = return_line_center(-1,'Cl',0.7)
            yield from bps.mov(zpssy, ycen)
            '''
            pass

        elif doAlignScan:
            if alignX[-1]:
                yield from fly1d(dets_fs,zpssx,alignX[0],alignX[1],alignX[2],alignX[3])
                xcen = return_line_center(-1,alignX[4],alignX[5])
                yield from bps.movr(smarx, xcen*0.001)
                print(f"zpssx centered to {xcen}")

            if alignY[-1]:
                yield from fly1d(dets_fs,zpssy,alignY[0],alignY[1],alignY[2],alignY[3])
                ycen = return_line_center(-1,alignX[4],alignY[5])
                yield from bps.movr(smary, ycen*0.001)
                print(f"zpssy centered to {ycen}")

        yield from bps.movr(smarx, +0.013)
        yield from bps.movr(smary, +0.013)


        print(f'Current scan: {i+1}/{len(e_list)}')

        # do the fly2d scan

        if dets == dets_fs: #for fast xanes scan, no transmission (merlin) in the list

            if doScan: yield from fly2d(dets, mot1,x_s,x_e,x_num,mot2,y_s,y_e,y_num,accq_t, dead_time=0.002) 
            #dead_time = 0.001 for 0.015 dwell

        else:

            if doScan: yield from fly2d(dets, mot1,x_s,x_e,x_num,mot2,y_s,y_e,y_num,accq_t)
        yield from bps.sleep(1)
        
        yield from bps.movr(smarx, -0.013)
        yield from bps.movr(smary, -0.013)


        #close fast shutter
        #caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0) 
        
        # after scan done go to 0,0 to rest
        #if doAlignScan: 
            #yield from bps.mov(zpssx, zpssx_i)
            #yield from bps.mov(zpssy, zpssy_i)

        #ycen, xcen = return_center_of_mass_blurr(-1,'S') 
        # some cases use 2D mass center for alignemnt
        #print(ycen,xcen)

        # get some scan details and add to the list of scan id and energy

        last_sid = int(caget('XF:03IDC-ES{Status}ScanID-I'))
        e_pos = e.position
        
        #Add more info to the dataframe
        e_list['E Readback'].at[i] = e_pos #add real energy to the dataframe
        e_list['Scan ID'].at[i] = int(last_sid) #add scan id to the dataframe
        e_list['TimeStamp'].at[i] = pd.Timestamp.now()
        e_list['IC3'].at[i] = ic_3 #Ic values are useful for calibration
        e_list['IC0'].at[i] = ic_0 #Ic values are useful for calibration
        e_list['Peak Flux'].at[i] = fluxPeaked # recoed if peakflux was excecuted
        e_list['IC3_before_peak'].at[i] = ic3_ #ic3 right after e change, no peaking
        fluxPeaked = False #reset
        
        if pdfLog:
            for elem in pdfElem:
                insert_xrf_map_to_pdf(-1,elem)# plot data and add to pdf

        # save the DF in the loop so quitting a scan won't affect
        filename = f"HXN_nanoXANES_StartID{int(e_list['Scan ID'][0])}_{len(e_list)}_e_points.csv"
        e_list.to_csv(os.path.join(saveLogFolder, filename), float_format= '%.5f')

    #go back to max energy point if scans done reverese
    max_e_id = e_list['energy'].idxmax()
    e_max, zpz_max, *others = e_list.iloc[max_e_id]
    
    if not np.isclose(e_list['energy'].max(), e.position):
    
        yield from move_energy(e_max,zpz_max)
        
        yield from peak_the_flux()

    
    else: pass
        
    caput('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0',0) 
    if pdfLog: save_page() #save the pdf

'''

bbpm_x = "XF:03ID-BI{EM:BPM1}fast_pidX.VAL"
bbpm_y = "XF:03ID-BI{EM:BPM1}fast_pidY.VAL"


def peak_b_bpm(bpm_name, start, end, n_steps):
    shutter_b_cls_status = caget('XF:03IDB-PPS{PSh}Sts:Cls-Sts')
    shutter_c_status = caget('XF:03IDC-ES{Zeb:2}:SOFT_IN:B0')


    if shutter_b_cls_status == 0:

        caput('XF:03IDC-ES{Status}ScanRunning-I', 1)
        bpm_0 = caget(bpm_name)
        x = np.linspace(bpm_0+start,bpm_0+end,n_steps+1)
        y = np.arange(n_steps+1)
        #print(x)
        for i in range(n_steps+1):
            caput(bpm_name,x[i])
            if i == 0:
                yield from bps.sleep(5)
            else:
                yield from bps.sleep(2)

            if shutter_c_status == 0:
                y[i] = sclr2_ch2.get()

            else:
                y[i] = sclr2_ch4.get()


        peak = x[y == np.max(y)]
        caput(bpm_name,peak[0])
        yield from bps.sleep(2)

    else:
        print('Shutter B is Closed')

'''

    #plt.pause(5)
    #plt.close()


    #zp_list_xanes2d(FeXANES, dets1, zpssx,-4,4,80,zpssy, -4,4,80,0.05, highEStart=False, alignX = (-5,5,100,0.05,0.5), alignY = (-5,5,100,0
   #...: .05,05), pdfElem=["Fe", "S"], saveLogFolder="\data\Staff\Ajith\2022Q2")"

#<zp_list_xanes2d(LuL3XANES, dets_fs, zpssx,-15,15,100,zpssy, -15,15,100,0.02, highEStart=False,  alignX = (-10,10,10
   #...: 0,0.05,"Au_M",0.5, True), alignY = (-10,10,100,0.05,"Au_M",0.5,True), pdfElem=["Lu_L", "Au_M"], peakBeam=False,saveLogFolder="/GPFS/XF03ID1/users/2022
   #...: Q2/Tyson_2022Q2")
#<zp_list_xanes2d(LuL3XANES, dets_fs, zpssx,-15,15,100,zpssy, -15,15,100,0.02, highEStart=False,  alignX = (-10,10,100,0.05,"Au_M",0.5, True), alignY = (-10
   #...: ,10,100,0.05,"Au_M",0.5,True), pdfElem=["Lu_L", "Au_M"], peakBeam=False,saveLogFolder="/GPFS/XF03ID1/users/2022Q2/Tyson_2022Q2")

#<zp_list_xanes2d(FeXANES, dets_fs, zpssx,-15,15,150,zpssy, -15,15,150,0.03, highEStart=False,  alignX = (-10,10,100,0.05,"Au_M",0.5, True), alignY = (-10
   #...: ,10,100,0.05,"Au_M",0.5,True), pdfElem=["Fe", "Au_M"], peakBeam=False,saveLogFolder="/GPFS/XF03ID1/users/2022Q2/Tyson_2022Q2")
