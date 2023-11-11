print(f"Loading {__file__!r} ...")

import logging
import numpy as np
import pandas as pd
import pyqtgraph as pg
import matplotlib.pyplot as plt
from epics import caget, caput

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger()

wd = "/nsls2/data/hxn/shared/config/bluesky/profile_collection/startup/"

class HXNEnergy():
    
    def __init__(self, ugap_,bragg_e, dcm_pitch, ic1, calib_file_csv):

        self.ugap = ugap_
        self.bragg_e = bragg_e
        self.dcm_pitch = dcm_pitch
        self.ic1 = ic1
        self.calib_file = calib_file_csv
        self.df = pd.read_csv(self.calib_file)
        self.calibrate_optics(False)
        self.defineFeedBackPVs()

    def defineFeedBackPVs(self):
        self.hcm_pf_sts = "XF:03IDC-CT{FbPid:01}PID:on"
        self.hfm_pf_sts = "XF:03IDC-CT{FbPid:02}PID:on"

        self.xbpm_x_rbv = "XF:03ID-BI{EM:BPM1}PosX:MeanValue_RBV"
        self.xbpm_y_rbv = "XF:03ID-BI{EM:BPM1}PosY:MeanValue_RBV"

        self.xbpm_x_val = "XF:03ID-BI{EM:BPM1}fast_pidX.VAL"
        self.xbpm_x_val = "XF:03ID-BI{EM:BPM1}fast_pidY.VAL"


    def get_values(self,targetE):

        u_gap, harmonics = self.gap(targetE, harmonicsChoice = -1)
        dcm_pitch = self.calculatePitch(targetE)
        dcm_roll = self.calculateRoll(targetE)
        hfm_pitch = self.calculateHFMPitch(targetE)
        mirror_coating = self.findAMirror(targetE)

        logger.info(f"{u_gap = :.1f}\n{harmonics = }\n{dcm_pitch = :.4f}\n"
                    f"{dcm_roll = :.4f}\n{hfm_pitch = :.4f}\n{mirror_coating = }")

        return u_gap, harmonics,dcm_pitch,dcm_roll,hfm_pitch,mirror_coating



    def calcGap(self,E,harmonics = 5, offset = 4):
        E1 = E/harmonics
        calc_gap =  np.polyval(self.ugap_coeffs, E1) + offset
        return (np.around(calc_gap,1))

    def gap(self,targetE, harmonicsChoice = -1):
        
        "Estimate a suitable gap for target energy"

        if harmonicsChoice == -1:
        
            harmonics = np.array([3,5,7,9]) #harmonics options

            if targetE>4.99 and targetE<25:     # if dialed a wrong number
                
                opt = np.array([self.calcGap(targetE, harmonics = hm) for hm in harmonics])
                idx = np.where(np.logical_and(opt>=6000, opt<=10000)) #6000 beacuse of the ugap scan limit
                gap =  opt[idx][-1] #last one has lowest gap in the list
                logger.info(f" estimated gap = {gap}")
                

                harmonic = harmonics[idx][-1]
                logger.info(f" Harmonic = {harmonic}")

                return gap, harmonic
            
            else:
                raise ValueError(" Requested Energy is out of range")
                return

        else:

            gap = self.calcGap(targetE, harmonics = int(harmonicsChoice))

            return gap, int(harmonicsChoice)
    
    
    def findAMirror(self,e):
    
        EnergyToMirror = {(5,8.5):'Si',(8.5,15):'Cr',(15,20):'Rh',(20,25):'Pt'}
    
        if not 4.99 <= e <= 25:
            raise ValueError (" Energy value out of range")
        
        else:
            for erange in EnergyToMirror.keys():
                if erange[0] <= e <= erange[1]:
                    return EnergyToMirror[erange]
                else:
                    pass
    

    def moveMirror(self,targetE, mirror = "auto"):
        
         MirrorPos = {'Si':(21,-4),'Cr':(5,15),'Rh':(30,-12),'Pt':(13.5,4)}         
         
         if mirror == "auto":
             foundMirror = self.findAMirror(targetE)
             positions = MirrorPos[foundMirror]
             logger.info(f"Moving to {foundMirror}")    
         else:
             positions = MirrorPos[mirror]
             logger.info(f"Moving to {mirror}")

         #caput("XF:03IDA-OP{Mir:1-Ax:Y}Mtr",positions[0])
         #caput("XF:03IDA-OP{Mir:2-Ax:Y}Mtr",positions[1])
         yield from bps.mov(m1.y, positions[0], m2.y, positions[1] )

    def calibrate_optics(self, plot_after = False):

        en = self.df["energy"].to_numpy()

        adj_E = en/self.df["harmonic"].to_numpy()
        ugaps = self.df["ugap"].to_numpy()
        self.ugap_coeffs = np.polyfit(adj_E, ugaps, 3)

        dcm_p = self.df["dcmPitch"].to_numpy()
        self.dcm_p_coeffs = np.polyfit(en, dcm_p, 3)

        m2_p = self.df["hfmPitch"].to_numpy()
        self.m2p_coeffs = np.polyfit(en, m2_p, 3)

        dcm_r = self.df["dcmRoll"].to_numpy()
        self.dcm_r_coeffs = np.polyfit(en, dcm_r, 3)

        if plot_after:

            fig, axs = plt.subplots(2,2,figsize = (8,8))
            fig.subplots_adjust(hspace = 0.8, wspace = 0.8)
            fig.suptitle("Energy Calibration")
            fig.show()
            axs = axs.ravel()

            axs[0].scatter(adj_E,ugaps,label='ugap')
            axs[0].plot(adj_E, np.polyval(self.ugap_coeffs, adj_E),'r', label='ugap_fit')
            axs[0].set_title("First order E vs Ugap")
            axs[0].set_xlabel("First Order Energy (keV)")
            axs[0].set_ylabel("undulator Gap (um)")

            axs[1].scatter(en,dcm_p,label='dcm_p')
            axs[1].plot(en, np.polyval(self.dcm_p_coeffs, en),'r', label='dcm_p_fit')
            axs[1].set_title("E vs dcm_pitch")
            axs[1].set_xlabel("Energy (keV)")
            axs[1].set_ylabel("dcm_pitch")

            axs[2].scatter(en,m2_p,label='m2_p')
            axs[2].plot(en, np.polyval(self.m2p_coeffs, en),'r', label='m2_p_fit')
            axs[2].set_title("E vs m2_pitch")
            axs[2].set_xlabel("Energy (keV)")
            axs[2].set_ylabel("m2_pitch")
            
            axs[3].scatter(en,dcm_r,label='dcm_r')
            axs[3].plot(en, np.polyval(self.dcm_r_coeffs, en),'r', label='dcm_r_fit')
            axs[3].set_title("E vs dcm_roll")
            axs[3].set_xlabel("Energy (keV)")
            axs[3].set_ylabel("dcm_roll")
        

    def calculatePitch(self,targetE, offset = 0):
        calc_pitch =  np.polyval(self.dcm_p_coeffs, targetE) + offset
        return np.around(calc_pitch,4) 

    def calculateRoll(self,targetE, offset = 0):
        calc_r =  np.polyval(self.dcm_r_coeffs, targetE)
        return (np.around(calc_r+offset,4))

    def calculateHFMPitch(self,targetE, offset = 0):
        calc_m2p =  np.polyval(self.m2p_coeffs, targetE)
        return (np.around(calc_m2p+offset,4))

    def move(self,targetE, harmChoice = -1, moveMonoPitch = True, moveMirror = "auto") :
        
        bbpm_auto = "XF:03ID{XBPM:17}AutoFbEn-Cmd"
        bbpm_x = "XF:03ID-BI{EM:BPM1}fast_pidX.FBON"
        bbpm_y = "XF:03ID-BI{EM:BPM1}fast_pidY.FBON"

        gap, hrm = Energy.gap(targetE,harmChoice)
        dcm_p_target = self.calculatePitch(targetE)
        hfm_p_target = self.calculateHFMPitch(targetE)
        dcm_r_target = self.calculateRoll(targetE)


        logger.info(f"{dcm_p_target = :.4f}, {hfm_p_target = :.2f}, {dcm_r_target = :.4f}")

        if gap<5200 and gap>10000:
            raise ValueError ("Incorrect gap calculation")
        else:
            #logger.info(f"Moving gap = {gap}")
            yield from bps.mov(ugap, gap)
            logger.info("Gap moved")
        
            logger.info(f"Mono Energy Target = {targetE}")
            
            try:
                yield from bps.mov(e,targetE, timeout = 180)
            except FailedStatus:
                yield from bps.mov(e,targetE, timeout = 180)
            except: raise Error("Mono motio failed")
                
                
            logger.info("Energy reached")

            if moveMonoPitch:

                    
                logger.info(f"Moving {dcm_p_target = :4f}")
                if abs(dcm_p_target)>2 or abs(dcm_r_target)>2 or abs(hfm_p_target)>2:
                    raise ValueError("Incorrect calculation of dcm_p, dcm_r ot hfm_p positions; aborting")
                else:
                    yield from bps.mov(dcm.p,dcm_p_target)
                    logger.info(f"Moving {dcm_r_target = :4f}")
                    yield from bps.mov(dcm.r,dcm_r_target)
                    logger.info(f"Moving {hfm_p_target = :4f}")
                    yield from bps.mov(m2.p, hfm_p_target)

                    #change merlin energy
                    caput("XF:03IDC-ES{Merlin:1}cam1:Acquire",0)
                    caput("XF:03IDC-ES{Merlin:1}cam1:OperatingEnergy", targetE)
                    
                    #change merlin energy
                    caput("XF:03IDC-ES{Merlin:2}cam1:Acquire",0)
                    caput("XF:03IDC-ES{Merlin:2}cam1:OperatingEnergy", targetE)
                

            if not moveMirror == "ignore":
                yield from self.moveMirror(targetE, moveMirror)
            
            logger.info("Energy change completed")




    
    def autoUGapCalibration(self,EStart = 8.5, EEnd = 9.5, EStep = 5):

        #Make sure strating energy is at optimized conditions and you have a  good beam at ssa2

        #change IC1 sensivity to 5 um
        #not that we are just caput the position of the value

                            #move out,FS if in 

        if caget('XF:03IDA-OP{FS:1-Ax:Y}Mtr.VAL')<-50:

            caput('XF:03IDA-OP{FS:1-Ax:Y}Mtr.VAL', -20.)
            yield from bps.sleep(10)
            #caput('XF:03IDC-OP{Stg:CAM6-Ax:X}Mtr.VAL', -50)



        caput("XF:03IDC-CT{SR570:1}sens_num.VAL",2)
        caput("XF:03IDC-CT{SR570:1}sens_unit.VAL",2)

        #open ssa2        
        caput('XF:03IDC-OP{Slt:SSA2-Ax:XAp}Mtr.VAL', 2)
        caput('XF:03IDC-OP{Slt:SSA2-Ax:YAp}Mtr.VAL', 2)



        #setm2pf to 10
        caput("XF:03IDA-OP{HFM:1-Ax:PF}Mtr.VAL", 10)

        ic1_init = sclr1_ch2.get()
        df = pd.DataFrame(columns = ["Time Stamp","energy","harmonic","ugap","dcmPitch",'dcmRoll', "hfmPitch", "IC1"], dtype = "object")

        ePoints = np.linspace(EStart, EEnd, EStep+1)
        df["energy"] = ePoints

        print(df.head())
        yield from bps.sleep(2)

        for i in tqdm.tqdm(range(len(ePoints)),desc = 'Undulator Energy Calibration'):

            while caget("XF:03IDA-OP{Mono-Shld:Comp}T-I")>-60:
                yield from bps.sleep(60)

            yield from check_for_beam_dump(1000)

        #for i in range(len(ePoints)):

            if sclr2_ch2.get() < ic1_init*0.25:
                raise RuntimeError ("Ion chamber value dropped; aborting calibration")

            if sclr2_ch2.get() < ic1_init*0.5:
                yield from bps.mov(ssa2.vgap,1)
                yield from Energy.fluxOptimizerScan(dcm.r,-0.03, 0.03, 12, ic = sclr2_ch2, moveToMax = True)
                yield from bps.mov(ssa2.vgap,2)

            target_e = df["energy"][i]

            gap_, hrm = Energy.gap(target_e)

            if abs(gap_-ugap.position)>2000 and gap_<5800 and gap_>10000:
                raise ValueError ("Incorrect gap calculation")
            else:
                logger.info(f"Moving gap = {gap_}")
                yield from bps.mov(ugap, gap_)
                logger.info("Gap moved")

            #yield from bps.mov(e,target_e)
            yield from Energy.move(target_e, moveMonoPitch=False)
            if sclr2_ch2.get() < ic1_init*0.5:
                yield from Energy.fluxOptimizerScan(dcm.r,-0.2, 0.2, 12, ic = sclr2_ch2, moveToMax = True)
                yield from Energy.fluxOptimizerScan(m2.p,-0.05, 0.05, 10, ic = sclr2_ch2, moveToMax = True)
            yield from bps.sleep(2)
            yield from Energy.fluxOptimizerScan(ugap,-40, 40, 40, ic = sclr2_ch2, moveToMax = True)
            #yield from fluxOptimizerScan(ugap,-5, 5, 10, ic = xbpm, moveToMax = True)
            #if i%2 == 0

            #dcm_p_target = Energy.calculatePitch(target_e)
            #yield from bps.mov(dcm.p,dcm_p_target)
            
            logger.info("performing m2_p course centering")
            yield from bps.mov(ssa2.hgap,1, ssa2.vgap,2)
            yield from Energy.fluxOptimizerScan(m2.p,-0.005, 0.005, 10, ic = sclr2_ch2, moveToMax = True)
            yield from Energy.fluxOptimizerScan(dcm.p,-0.01, 0.01, 10, ic = sclr2_ch2, moveToMax = True)
            yield from bps.mov(ssa2.hgap,2, ssa2.vgap,1)
            yield from Energy.fluxOptimizerScan(dcm.r,-0.01, 0.01, 10, ic = sclr2_ch2, moveToMax = True)

           
            logger.info("optimize beam at ssa2")
            #yield from find_beam_at_ssa2(500,1)
            m2_p = m2.p.position
            yield from bps.mov(m2.pf, 10)
            yield from bps.mov(m2.p,m2_p)
            yield from bps.sleep(5)


            df["Time Stamp"].at[i] = pd.Timestamp.now()
            df['harmonic'].at[i] = hrm
            df['ugap'].at[i] = ugap.position
            df['dcmPitch'].at[i] = dcm.p.position
            df['dcmRoll'].at[i] = dcm.r.position
            df['hfmPitch'].at[i] = m2.p.position
            df['IC1'].at[i] = sclr2_ch2.get()
            df.to_csv(wd+"ugap_calib_09122023.csv",float_format= '%.5f')
            plt.close('all')

            ugap_offset = ugap.position - gap_
            logger.info(f"Gap offset: {ugap_offset :.1f}")

        adj_E = df["energy"].to_numpy()/df["harmonic"].to_numpy()
        E_Ugap_fit = np.polyfit(adj_E, df["ugap"].to_numpy(),3)
        print(E_Ugap_fit)

        plt.figure()
        plt.scatter(adj_E,df["ugap"],label='data')
        plt.plot(adj_E, np.polyval(E_Ugap_fit, adj_E),'r', label='fit'+str(np.around(E_Ugap_fit,1)))
        plt.xlabel("First Order Energy (keV)")
        plt.ylabel("undulator Gap (um)")
        plt.legend()
        plt.title(f"Undulator Calib_{pd.Timestamp.now().month}_{pd.Timestamp.now().year}")
        plt.show()





    @staticmethod
    def fluxOptimizerScan(motor,rel_start, rel_end, steps, ic = sclr2_ch2, moveToMax = True):
        #TODO replace with a step scan
  
        MtrPos = motor.position


        x = np.linspace(MtrPos+rel_start, MtrPos+rel_end, steps+1)
        y = np.arange(steps+1)

        
        for i in tqdm.tqdm(y,desc = "peaking "+str(motor.name)):

            yield from bps.mov(motor, x[i])
            
            if motor == m2.p:
                yield from bps.sleep(4)

            else:

                yield from bps.sleep(2)
            
            if ic==xbpm:
                y[i] = caget("XF:03ID-BI{EM:BPM1}SumAll:MeanValue_RBV")

            else:
            
                y[i] = ic.get()


        peakPos = x[y == np.max(y)][-1]

        plt.figure()
        plt.title(motor.name)
        plt.plot(x,y)


        if moveToMax:

            yield from bps.mov(motor, peakPos)
        
        else:
            yield from bps.mov(motor, MtrPos)
            #print(peakPos)
            return peakPos
            
            
    def fluxOptimizerScan2(motor,rel_start, rel_end, steps, ic = sclr2_ch2, moveToMax = True):
        #TODO replace with a step scan
  
  
        yield from dscan([zebra,sclr1], MtrPos, rel_start, rel_end, steps)
        MtrPos = motor.position


        x = np.linspace(MtrPos+rel_start, MtrPos+rel_end, steps+1)
        y = np.arange(steps+1)

        
        for i in tqdm.tqdm(y,desc = "peaking "+str(motor.name)):

            yield from bps.mov(motor, x[i])
            
            if motor == m2.p:
                yield from bps.sleep(4)

            else:

                yield from bps.sleep(2)
            
            if ic==xbpm:
                y[i] = caget("XF:03ID-BI{EM:BPM1}SumAll:MeanValue_RBV")

            else:
            
                y[i] = ic.get()


        peakPos = x[y == np.max(y)][-1]

        plt.figure()
        plt.title(motor.name)
        plt.plot(x,y)


        if moveToMax:

            yield from bps.mov(motor, peakPos)
        
        else:
            yield from bps.mov(motor, MtrPos)
            #print(peakPos)
            return peakPos

def plot_calib_results(csv_file):

    df = pd.read_csv(csv_file)
    adj_E = df["energy"].to_numpy()/df["harmonic"].to_numpy()
    E_Ugap_fit = np.polyfit(adj_E, df["ugap"].to_numpy(),3)
    print(E_Ugap_fit)

    plt.figure()
    plt.scatter(adj_E,df["ugap"],label='data')
    plt.plot(adj_E, np.polyval(E_Ugap_fit, adj_E),'r', label='fit'+str(np.around(E_Ugap_fit,1)))
    plt.xlabel("First Order Energy (keV)")
    plt.ylabel("undulator Gap (um)")
    plt.legend()
    plt.title(f"Undulator Calib_{pd.Timestamp.now().month}_{pd.Timestamp.now().year}")
    plt.show()

def foil_calib_scan(startE, endE,saveLogFolder):

    """absolute energy"""
    
    energies = np.arange(startE,endE,0.0005)
    
    print(len(energies))
    
    e_list = pd.DataFrame()
    e_list['TimeStamp'] = pd.Timestamp.now()
    e_list['energy'] = energies
    e_list['E Readback'] = energies
    e_list['IC3'] = sclr2_ch4.get()
    e_list['IC0'] = sclr2_ch2.get()

    print(e_list.head())
    
    time_ = datetime.now().strftime("%Y-%m-%d %H:%M:%S")


    for i,en in tqdm.tqdm(enumerate(energies)):
        print (i/len(energies))

        yield from Energy.move(en, moveMonoPitch=False, moveMirror = "ignore")
        yield from bps.sleep(2)
        e_list['TimeStamp'].at[i] = pd.Timestamp.now()
        e_list['IC3'].at[i] = sclr2_ch4.get() 
        e_list['IC0'].at[i] = sclr2_ch2.get()
        e_list['E Readback'].at[i] = e.position #add real energy to the dataframe

        filename = f'HXN_nanoXANES_calib_{time_}.csv'
        #filename = f'HXN_nanoXANES_calib.csv'
        e_list.to_csv(os.path.join(saveLogFolder, filename), float_format= '%.5f')

        

    plt.figure()
    spec = -1*np.log(e_list['IC3'].to_numpy()/e_list['IC0'].to_numpy())
    plt.plot(e_list['E Readback'], spec)
    plt.plot(e_list['E Readback'], np.gradient(spec))
    plt.savefig(os.path.join(saveLogFolder, f'HXN_nanoXANES_calib_{time_}.png'))
    plt.show()



def foil_calib_d2_scan(startE, endE,saveLogFolder = "/data/users/current_user"):

    """absolute start and end E"""

    dE = endE-startE
    dUgap = Energy.calcGap(endE)-Energy.calcGap(startE)
    
    yield from Energy.move(startE, moveMonoPitch=False)
    yield from d2scan(dets_fs,100, e, 0, dE, ugap, 0, dUgap, 1)

    h = db[-1]
    sd = h.start["scan_id"]

    df = h.table()
    plt.figure()

    en_ = np.array(df['energy'],dtype=np.float32) 
    I = np.array(df['sclr1_ch4'],dtype=np.float32) 
    Io = np.array(df['sclr1_ch2'],dtype=np.float32) 
    spec = -1*np.log(I/Io)
    plt.plot(en_, spec, label = "xanes")
    plt.plot(en_, np.gradient(spec),label = "derivative")
    plt.savefig(os.path.join(saveLogFolder, f'HXN_nanoXANES_calib_{sd}.png'))
    #bps.sleep(2)
    plt.legend()
    plt.show()
    
def plot_foil_calib(sid=-1, saveLogFolder = "/data/users/current_user"):
    
    h = db[int(sid)]
    sd = h.start["scan_id"]

    df = h.table()
    plt.figure()

    en_ = np.array(df['energy'],dtype=np.float32) 
    I = np.array(df['sclr1_ch4'],dtype=np.float32) 
    Io = np.array(df['sclr1_ch2'],dtype=np.float32) 
    spec = -1*np.log(I/Io)
    plt.plot(en_, spec, label = "xanes")
    plt.plot(en_, np.gradient(spec),label = "derivative")
    plt.savefig(os.path.join(saveLogFolder, f'HXN_nanoXANES_calib_{sd}.png'))
    #bps.sleep(2)
    plt.legend()
    plt.show()


def peak_hfm_pitch(fine = False, tweak_range = 0.005):

    if fine:
        yield from Energy.fluxOptimizerScan(m2.pf,-1*tweak_range ,tweak_range,10)
    else:
        yield from Energy.fluxOptimizerScan(m2.p,-1*tweak_range,tweak_range,10)


def peak_dcm_roll(tweak_range = 0.005):

    yield from Energy.fluxOptimizerScan(dcm.r,-1*tweak_range,tweak_range,10)


Energy = HXNEnergy(ugap,e,dcm.p, "ic3", wd+"ugap_calib_09122023.csv")

#/home/xf03id/.ipython/profile_collection/startup/ugap_calib_06152023.csv
