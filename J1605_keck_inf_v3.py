import cPickle,numpy,pyfits
import pymc
from pylens import *
from imageSim import SBModels,convolve,SBObjects
import indexTricks as iT
from SampleOpt import AMAOpt
import pylab as pl
import numpy as np
from pylens import lensModel


# 0.02 arcsec/pixel
# HST: 0.05 arcsec/pixel --> so need to scale and somehow recentre.
# p_k = p_h * 2.5

def MakeCuts():
    image = pyfits.open('/data/mauger/EELs/SDSSJ1605+3811/J1605_Kp_narrow_med.fits')[0].data.copy()[550:750,600:850]
    header = pyfits.open('/data/mauger/EELs/SDSSJ1605+3811/J1605_Kp_narrow_med.fits')[0].header
    pyfits.writeto('/data/ljo31/Lens/J1605/J1605_Kp_narrow_med_cutout.fits',image,header,clobber=True)

def MakeMaps():
    image = pyfits.open('/data/mauger/EELs/SDSSJ1605+3811/J1605_Kp_narrow_med.fits')[0].data.copy()
    header = pyfits.open('/data/mauger/EELs/SDSSJ1605+3811/J1605_Kp_narrow_med.fits')[0].header
    cut1 = image[680:725,525:575]
    cut2 = image[700:750,850:925]
    cut3 = image[525:575,865:950]
    var1,var2,var3 = np.var(cut1),np.var(cut2),np.var(cut3)
    poisson = np.mean((var1,var2,var3))
    sigma = poisson**0.5
    im = pyfits.open('/data/ljo31/Lens/J1605/J1605_Kp_narrow_med_cutout.fits')[0].data.copy()
    smooth = ndimage.gaussian_filter(im,0.7)
    noisemap = np.where((smooth>0.7*sigma)&(im>0),im/120.+poisson, poisson)**0.5 # for now - nut find out the actual exposure time from Matt...
    pyfits.writeto('/data/ljo31/Lens/J1605/J1605_Kp_narrow_med_sigma.fits',noisemap,header,clobber=True)
    pl.figure()
    pl.imshow(noisemap)
    pl.colorbar()

# plot things
def NotPlicely(image,im,sigma):
    ext = [0,image.shape[0],0,image.shape[1]]
    #vmin,vmax = numpy.amin(image), numpy.amax(image)
    pl.figure()
    pl.subplot(221)
    pl.imshow(image,origin='lower',interpolation='nearest',extent=ext,vmin=0,vmax=8) #,vmin=vmin,vmax=vmax)
    pl.colorbar()
    pl.title('data')
    pl.subplot(222)
    pl.imshow(im,origin='lower',interpolation='nearest',extent=ext,vmin=0,vmax=8) #,vmin=vmin,vmax=vmax)
    pl.colorbar()
    pl.title('model')
    pl.subplot(223)
    pl.imshow(image-im,origin='lower',interpolation='nearest',extent=ext,vmin=-0.25,vmax=0.25)
    pl.colorbar()
    pl.title('data-model')
    pl.subplot(224)
    pl.imshow((image-im)/sigma,origin='lower',interpolation='nearest',extent=ext,vmin=-5,vmax=5)
    pl.title('signal-to-noise residuals')
    pl.colorbar()
    #pl.suptitle(str(V))
    #pl.savefig('/data/ljo31/Lens/TeXstuff/plotrun'+str(X)+'.png')

image = pyfits.open('/data/ljo31/Lens/J1605/J1605_Kp_narrow_med_cutout.fits')[0].data.copy()
sigma = pyfits.open('/data/ljo31/Lens/J1605/J1605_Kp_narrow_med_sigma.fits')[0].data.copy()
#sigma = np.ones(sigma.shape)*sigma[0,0]
yc,xc = iT.coords(image.shape)*0.2

# Model the PSF as a Gaussian to start with. We'll do this over a grid of sigmas, and then maybe also ellitpicity and position anlge (will get kompliziert!!)
xp,yp = iT.coords((170,170))-85
OVRS = 1

# we should get these from the iterated terminal version.
#det = np.load('/data/ljo31/Lens/J1605/det8.npy')[()]
det = np.load('/data/ljo31/Lens/J1605/det10.npy')[()] # this has the galaxies and sources coincident in space.

g1,g2,l1,s1,s2,sh = {},{},{},{},{},{}

srcs = []
gals = []
lenses = []
coeff=[]
for name in det.keys():
    s = det[name]
    coeff.append(s[-1])
    if name[:8] == 'Source 1':
        s1[name[9:]] = s[-1]
    elif name[:8] == 'Source 2':
        s2[name[9:]] = s[-1]
    elif name[:6] == 'Lens 1':
        l1[name[7:]] = s[-1]
    elif name[:8] == 'Galaxy 1':
        g1[name[9:]] = s[-1]
    elif name[:8] == 'Galaxy 2':
        g2[name[9:]] = s[-1]
    elif name[:8] == 'extShear':
        if len(name)<9:
            sh['b'] = s[-1]
        elif name == 'extShear PA':
            sh['pa'] = s[-1]
    
s2['x'] = s1['x'].copy()
s2['y'] = s1['y'].copy()
g2['x'] = g1['x'].copy()
g2['y'] = g1['y'].copy()
srcs.append(SBModels.Sersic('Source 1',s1))
srcs.append(SBModels.Sersic('Source 2',s2))
gals.append(SBModels.Sersic('Galaxy 1',g1))
gals.append(SBModels.Sersic('Galaxy 2',g2))
lenses.append(MassModels.PowerLaw('Lens 1',l1))
sh['x'] = lenses[0].pars['x']
sh['y'] = lenses[0].pars['y']
lenses.append(MassModels.ExtShear('shear',sh))


## try some way of fitting!
#pars = [xoffset,yoffset,sig]
pars = []
cov = []
pars.append(pymc.Uniform('xoffset',9,13,value=10.5))
pars.append(pymc.Uniform('yoffset',10,14,value=12))
cov += [5,5] # think about this!
pars.append(pymc.Uniform('sigma 1',0,8,value=4))
cov += [5]
pars.append(pymc.Uniform('q 1',0,1,value=0.7))
cov += [1]
pars.append(pymc.Uniform('pa 1',-180,180,value= 90 )) #-30 )) #-30.0))
cov += [50]
pars.append(pymc.Uniform('amp 1',0,1,value=0.7))
cov += [4]
pars.append(pymc.Uniform('sigma 2',0,150,value= 100 )) #30eb )) #15))
cov += [40]
pars.append(pymc.Uniform('q 2',0,1,value=0.9))
cov += [1]
pars.append(pymc.Uniform('pa 2',-180,180,value= 90 )) #-100 )) ##-100))
cov += [100]


@pymc.deterministic
def logP(value=0,p=pars):
    x0 = pars[0].value
    y0 = pars[1].value
    sig1 = pars[2].value.item()
    q1 = pars[3].value.item()
    pa1 = pars[4].value.item()
    amp1 = pars[5].value.item()
    sig2 = pars[6].value.item()
    q2 = pars[7].value.item()
    pa2 = pars[8].value.item()
    amp2 = 1.-amp1
    psfObj1 = SBObjects.Gauss('psf 1',{'x':0,'y':0,'sigma':sig1,'q':q1,'pa':pa1,'amp':10})
    psfObj2 = SBObjects.Gauss('psf 2',{'x':0,'y':0,'sigma':sig2,'q':q2,'pa':pa2,'amp':10})
    psf1 = psfObj1.pixeval(xp,yp) * amp1 / (np.pi*2.*sig1**2.)
    psf2 = psfObj2.pixeval(xp,yp) * amp2 / (np.pi*2.*sig2**2.)
    psf = psf1 + psf2
    psf /= psf.sum()
    psf = convolve.convolve(image,psf)[1]
    return lensModel.lensFit(None,image,sigma,gals,lenses,srcs,xc+x0,yc+y0,1,
                                verbose=False,psf=psf,csub=1)

@pymc.observed
def likelihood(value=0.,lp=logP):
    return lp

def resid(p):
    lp = -2*logP.value
    return self.imgs[0].ravel()*0 + lp

optCov = None
if optCov is None:
    optCov = numpy.array(cov)

# use lensFit to calculate the likelihood at each point in the chain
for i in range(1):
    S = AMAOpt(pars,[likelihood],[logP],cov=optCov/4.)
    S.set_minprop(len(pars)*2)
    S.sample(450*len(pars)**2)

logp,trace,det = S.result() # log likelihoods; chain (steps * params); det['extShear PA'] = chain in this variable
coeff = []
for i in range(len(pars)):
    coeff.append(trace[-1,i])

coeff = numpy.asarray(coeff)
pars = coeff
o = 'npars = ['
for i in range(pars.size):
    o += '%f,'%(pars)[i]
o = o[:-1]+"]"

keylist = []
dkeylist = []
chainlist = []
for key in det.keys():
    keylist.append(key)
    dkeylist.append(det[key][-1])
    chainlist.append(det[key])

plot = False
if plot:
    for i in range(len(keylist)):
        pl.figure()
        pl.plot(chainlist[i])
        pl.title(str(keylist[i]))

# compare best model with data!
sigma = pyfits.open('/data/ljo31/Lens/J1605/J1605_Kp_narrow_med_sigma.fits')[0].data.copy()
x0 = det['xoffset'][-1]
y0 = det['yoffset'][-1]
sig1 = det['sigma 1'][-1]
q1 = det['q 1'][-1]
pa1 = det['pa 1'][-1]
amp1 = det['amp 1'][-1]
sig2 = det['sigma 2'][-1]
q2 = det['q 2'][-1]
pa2 = det['pa 2'][-1]
amp2 = 1.-amp1
psfObj1 = SBObjects.Gauss('psf 1',{'x':0,'y':0,'sigma':sig1,'q':q1,'pa':pa1,'amp':10})
psfObj2 = SBObjects.Gauss('psf 2',{'x':0,'y':0,'sigma':sig2,'q':q2,'pa':pa2,'amp':10})
psf1 = psfObj1.pixeval(xp,yp) * amp1 / (2.*np.pi*sig1**2)
psf2 = psfObj2.pixeval(xp,yp) * amp2 / (2.*np.pi*sig2**2)
psf = psf1 + psf2
psf /= psf.sum()
psf = convolve.convolve(image,psf)[1]
im = lensModel.lensFit(coeff,image,sigma,gals,lenses,srcs,xc+x0,yc+y0,OVRS,noResid=True,psf=psf,verbose=True) # return model
model = lensModel.lensFit(coeff,image,sigma,gals,lenses,srcs,xc+x0,yc+y0,OVRS,noResid=True,psf=psf,verbose=True,getModel=True,showAmps=True)

NotPlicely(image,im,sigma)
pl.savefig('/data/ljo31/Lens/J1605/Keckpsf.eps')

for key in det.keys():
    print key, det[key][-1]

print 'KECK - x & y & sigma 1 & sigma 2 & pa 1 & pa 2 & q 1 & q 2 & amp 1 \\'
print '%.1f'%det['xoffset'][-1], '&', '%.1f'%det['yoffset'][-1], '&', '%.1f'%det['sigma 1'][-1], '&', '%.1f'%det['sigma 2'][-1], '&', '%.1f'%det['pa 1'][-1], '&', '%.1f'%det['pa 2'][-1], '&', '%.1f'%det['q 1'][-1], '&', '%.1f'%det['q 2'][-1], '&', '%.1f'%det['amp 1'][-1], '\\'
