# -*- coding: utf-8 -*-
"""
Created on Tue Sep 22 14:43:24 2015

@author: Lindsay
"""
## whatever units we have, we want a cntral aperture of radius 1m and outer aperture radius 3m. b0 = 20cm. Interactutator distance = 7mm!
## a code to model the Keck AO PSF a la Leon Koopmans Leon - 20 arcsec separation between guide star and object. 10m distance to where the seeing happens in the atmosphere.

## (1) make a grid of the aperture function of the telescope
import indexTricks as iT
import numpy as np
import pylab as pl

grid = np.zeros((1024,1024))
y,x = iT.coords(grid.shape)
y,x = y-512.,x-512.
R = np.sqrt(y**2. + x**2.)
b_max = 50
grid[R<b_max] = 1
grid[R<10] = 0
# find out what these values should be!

#pl.figure()
#pl.imshow(grid,interpolation='nearest')
#pl.colorbar()

# (2) cross-correlate A(x) with itself - do this via FFT on a grid
from numpy import fft
fgrid = fft.fft2(grid)
fgrid = fft.fftshift(fgrid)
#pl.figure()
#pl.imshow(abs(fgrid),interpolation='nearest')
abgrid = abs(fgrid)
fgrid2 = abgrid**2.
#pl.figure()
#pl.imshow(fgrid2, interpolation='nearest')
fgrid3 = fft.ifftshift(fgrid2)
grid = fft.ifft2(fgrid3)
factor = grid[511,511]
n = grid/factor
n = np.real(n)
#pl.figure()
#pl.imshow(n,interpolation='nearest')

# construct the window function, also on a grid
W = np.zeros(grid.shape)
b_act = 10
W[R>b_act] = 1
W[R>b_max] = 0
#pl.imshow(W)
I = np.ones(grid.shape)
b0=100
D = (R/b0)**(5./3.)
G1 = n * W
G2 = n * (I-W) * np.exp(-0.5*D)

#pl.figure()
#pl.imshow(G2,interpolation='nearest')

psf = fft.fft2(G1 + G2)
psf = fft.fftshift(psf)
psf = abs(psf)
print np.sum(psf)
psf = psf/np.sum(psf)
pl.figure()
pl.imshow(psf)
## strehl ratio - is it sensible?
strehl = n
strehl = fft.fft2(strehl)
strehl = fft.fftshift(strehl)
strehl = abs(strehl)
print np.sum(strehl)
strehl = strehl/np.sum(strehl)
pl.figure()
pl.imshow(strehl)
print np.amax(strehl)
print np.amax(psf)
print np.amax(psf)/np.amax(strehl)
# Good. Now we just have to work out the proper parameter values for b_act, b_max, b_0
pl.figure()
sort = np.argsort(np.ravel(R))
pl.plot(np.ravel(R)[sort], np.ravel(psf)[sort])
pl.plot(np.ravel(R)[sort], np.ravel(strehl)[sort])

'''


I = np.ones(grid.shape)
## (4) D_phi = (b/b0)**5/3 where b0 is the Fried length - this is related to the seeing, which we should know. Look up the relation in the literature
b0 = 5.
#seeing = 0.7 # arcseconds
#wl = 606e-9
#b0 = 0.98 * wl / seeing
print b0
# what is the seeing?!?
'''
