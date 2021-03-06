
# -*- coding: utf-8 -*-

u'''Functions L{parseUTMUPS5}, L{toUtmUps8},  L{UtmUps} and
L{utmupsZoneBand5} to handle both I{Universal Transverse Mercator
(U{UTM<https://WikiPedia.org/wiki/Universal_Transverse_Mercator_coordinate_system>})}
and I{Universal Polar Stereographic
(U{UPS<https://WikiPedia.org/wiki/Universal_polar_stereographic_coordinate_system>})}
coordinates.

A pure Python implementation, partially transcribed from C++ class U{UTMUPS
<https://GeographicLib.SourceForge.io/html/classGeographicLib_1_1UTMUPS.html>}
by I{Charles Karney}.
'''

from pygeodesy.basics import map1
from pygeodesy.datum import Datums
from pygeodesy.errors import _IsnotError, RangeError, _ValueError, _xkwds_get
from pygeodesy.interns import _easting_, _MGRS_, NN, _northing_, _NS_, \
                              _outside_, _range_, _SPACE_, _UPS_, _UTM_
from pygeodesy.lazily import _ALL_LAZY
from pygeodesy.named import modulename
from pygeodesy.ups import parseUPS5, toUps8, Ups, UPSError, upsZoneBand5
from pygeodesy.utm import parseUTM5, toUtm8, Utm, UTMError, utmZoneBand5
from pygeodesy.utmupsBase import _MGRS_TILE, _to4lldn, _to3zBhp, \
                                 _UPS_ZONE, _UPS_ZONE_STR, \
                                 _UTMUPS_ZONE_MIN, _UTMUPS_ZONE_MAX, \
                                  UtmUps5Tuple, UtmUps8Tuple  # PYCHOK indent

__all__ = _ALL_LAZY.utmups
__version__ = '20.07.08'

_UPS_N_MAX = 27 * _MGRS_TILE
_UPS_N_MIN = 13 * _MGRS_TILE
_UPS_S_MAX = 32 * _MGRS_TILE
_UPS_S_MIN =  8 * _MGRS_TILE

_UTM_C_MAX =   9 * _MGRS_TILE
_UTM_C_MIN =   1 * _MGRS_TILE
_UTM_N_MAX =  95 * _MGRS_TILE
_UTM_N_MIN =   0 * _MGRS_TILE
_UTM_S_MAX = 100 * _MGRS_TILE
_UTM_S_MIN =  10 * _MGRS_TILE

_UTM_N_SHIFT = _UTM_S_MAX - _UTM_N_MIN  # South minus North UTM northing


class _UpsMinMax(object):  # XXX _NamedEnum or _NamedTuple
    # UPS ranges for North, South pole
    eMax = _UPS_N_MAX, _UPS_S_MAX
    eMin = _UPS_N_MIN, _UPS_S_MIN
    nMax = _UPS_N_MAX, _UPS_S_MAX
    nMin = _UPS_N_MIN, _UPS_S_MIN


class _UtmMinMax(object):  # XXX _NamedEnum or _NamedTuple
    # UTM ranges for Northern, Southern hemisphere
    eMax =  _UTM_C_MAX, _UTM_C_MAX
    eMin =  _UTM_C_MIN, _UTM_C_MIN
    nMax =  _UTM_N_MAX, (_UTM_N_MAX + _UTM_N_SHIFT)
    nMin = (_UTM_S_MIN - _UTM_N_SHIFT), _UTM_S_MIN


class UTMUPSError(_ValueError):  # XXX (UTMError, UPSError)
    '''Universal Transverse Mercator/Universal Polar Stereographic
       (UTM/UPS) parse, validate or other issue.
    '''
    pass


def parseUTMUPS5(strUTMUPS, datum=Datums.WGS84, Utm=Utm, Ups=Ups, name=NN):
    '''Parse a string representing a UTM or UPS coordinate, consisting
       of C{"zone[band] hemisphere/pole easting northing"}.

       @arg strUTMUPS: A UTM or UPS coordinate (C{str}).
       @kwarg datum: Optional datum to use (L{Datum}).
       @kwarg Utm: Optional class to return the UTM coordinate (L{Utm})
                   or C{None}.
       @kwarg Ups: Optional class to return the UPS coordinate (L{Ups})
                   or C{None}.
       @kwarg name: Optional name (C{str}).

       @return: The UTM or UPS coordinate (B{C{Utm}} or B{C{Ups}}) or
                a L{UtmUps5Tuple}C{(zone, hemipole, easting, northing,
                band)} if B{C{Utm}} respectively B{C{Ups}} or both are
                C{None}.  The C{hemipole} is C{'N'|'S'}, the UTM hemisphere
                or UPS pole, the UPS projection top/center.

       @raise UTMUPSError: Invalid B{C{strUTMUPS}}.

       @see: Functions L{parseUTM5} and L{parseUPS5}.
    '''
    try:
        try:
            u = parseUTM5(strUTMUPS, datum=datum, Utm=Utm, name=name)
        except UTMError:
            u = parseUPS5(strUTMUPS, datum=datum, Ups=Ups, name=name)
        return u

    except (UTMError, UPSError) as x:
        raise UTMUPSError(strUTMUPS=strUTMUPS, txt=str(x))


def toUtmUps8(latlon, lon=None, datum=None, falsed=True, Utm=Utm, Ups=Ups,
                                            pole=NN, name=NN, **cmoff):
    '''Convert a lat-/longitude point to a UTM or UPS coordinate.

       @arg latlon: Latitude (C{degrees}) or an (ellipsoidal)
                    geodetic C{LatLon} point.
       @kwarg lon: Optional longitude (C{degrees}) or C{None}.
       @kwarg datum: Optional datum to use this UTM coordinate,
                     overriding B{C{latlon}}'s datum (C{Datum}).
       @kwarg falsed: False both easting and northing (C{bool}).
       @kwarg Utm: Optional class to return the UTM coordinate (L{Utm})
                   or C{None}.
       @kwarg Ups: Optional class to return the UPS coordinate (L{Ups})
                   or C{None}.
       @kwarg pole: Optional top/center of UPS (stereographic)
                    projection (C{str}, C{'N[orth]'} or C{'S[outh]'}).
       @kwarg name: Optional name (C{str}).
       @kwarg cmoff: DEPRECATED, use B{C{falsed}}.  Offset longitude
                     from zone's central meridian, for UTM only (C{bool}).

       @return: The UTM or UPS coordinate (B{C{Utm}} respectively B{C{Ups}})
                or a L{UtmUps8Tuple}C{(zone, hemipole, easting, northing,
                band, datum, convergence, scale)} if B{C{Utm}} respectively
                B{C{Ups}} is C{None} or B{C{cmoff}} is C{False}.

       @raise RangeError: If B{C{lat}} outside the valid UTM or UPS bands
                          or if B{C{lat}} or B{C{lon}} outside the valid
                          range and L{rangerrors} set to C{True}.

       @raise TypeError: If B{C{latlon}} is not ellipsoidal or B{C{lon}}
                         value is missing.

       @raise UTMUPSError: UTM or UPS validation failed.

       @raise ValueError: Invalid B{C{lat}} or B{C{lon}}.

       @see: Functions L{toUtm8} and L{toUps8}.
    '''
    lat, lon, d, name = _to4lldn(latlon, lon, datum, name)
    z, B, p, lat, lon = utmupsZoneBand5(lat, lon)

    f = falsed and _xkwds_get(cmoff, cmoff=True)
    if z == _UPS_ZONE:
        u = toUps8(lat, lon, datum=d, falsed=f, Ups=Ups, pole=pole or p, name=name)
    else:
        u = toUtm8(lat, lon, datum=d, falsed=f, Utm=Utm, name=name)
    return u


def UtmUps(zone, hemipole, easting, northing, band=NN, datum=Datums.WGS84,
                                              falsed=True, name=NN):
    '''Class-like function to create a UTM/UPS coordinate.

       @kwarg zone: The UTM (longitudinal) zone with/-out Band letter
                    for UTM or for UPS zone C{"00"} or C{0} (C{str} or
                    C{int}).
       @kwarg hemipole: UTM hemisphere or UPS top/center of projection
                        (C{str}, C{'N[orth]'} or C{'S[outh]'}).
       @arg easting: Easting, see B{C{falsed}} (C{meter}).
       @arg northing: Northing, see B{C{falsed}} (C{meter}).
       @kwarg band: Optional, UTM (latitudinal) Band letter
                    C{'C'|'D'..'W'|'X'} or UPS (polar) Band letter
                    C{'A'|'B'|'Y'|'Z'} (C{str}).
       @kwarg datum: Optional, the coordinate's datum (L{Datum}).
       @kwarg falsed: Both B{C{easting}} and B{C{northing}} are falsed (C{bool}).
       @kwarg name: Optional name (C{str}).

       @return: New UTM or UPS instance (L{Utm} or L{Ups}).

       @raise UTMUPSError: UTM or UPS validation failed.

       @see: Classes L{Utm} and L{Ups} and Karney's U{UTMUPS
             <https://GeographicLib.SourceForge.io/html/classGeographicLib_1_1UTMUPS.html>}.
    '''
    z, B, hp = _to3zBhp(zone, band, hemipole=hemipole)
    U = Ups if z in (_UPS_ZONE, _UPS_ZONE_STR) else Utm
    return U(z, hp, easting, northing, band=B, datum=datum, falsed=falsed, name=name)


def utmupsValidate(coord, falsed=False, MGRS=False, Error=UTMUPSError):
    '''Check a UTM or UPS coordinate.

       @arg coord: The UTM or UPS coordinate (L{Utm}, L{Ups} or C{5+Tuple}).
       @kwarg falsed: C{5+Tuple} easting and northing are falsed (C{bool}).
       @kwarg MGRS: Increase easting and northing ranges (C{bool}).
       @kwarg Error: Optional error to raise, overriding the default
                     (L{UTMUPSError}).

       @return: C{None} if validation passed.

       @raise Error: Validation failed.

       @see: Function L{utmupsValidateOK}.
    '''

    def _en(en, lo, hi, ename):  # U, Error
        try:
            if lo <= float(en) <= hi:
                return
        except (TypeError, ValueError):
            pass
        t = _SPACE_.join((_outside_, U, _range_, '[%.0F' % (lo,),
                                                 '%.0F]' % (hi,)))
        raise Error(ename, en, txt=t)

    if isinstance(coord, (Ups, Utm)):
        zone = coord.zone
        hemi = coord.hemisphere
        e, n = coord.easting, coord.northing
        band = coord.band
        enMM = coord.falsed
    elif isinstance(coord, (UtmUps5Tuple, UtmUps8Tuple)):
        zone = coord.zone
        hemi = coord.hemipole
        e, n = coord.easting, coord.northing
        band = coord.band
        enMM = falsed
    else:
        raise _IsnotError(Error=Error, coord=coord, *map1(modulename,
                          Utm, Ups, UtmUps5Tuple, UtmUps8Tuple))

    z, B, h = _to3zBhp(zone, band, hemipole=hemi)

    if z == _UPS_ZONE:  # UPS
        import pygeodesy.ups as u  # PYCHOK expected
        U, M = _UPS_, _UpsMinMax
    else:  # UTM
        import pygeodesy.utm as u  # PYCHOK expected
        U, M = _UTM_, _UtmMinMax

    if MGRS:
        U, s = _MGRS_, _MGRS_TILE
    else:
        s = 0

    i = _NS_.find(h)
    if i < 0 or z < _UTMUPS_ZONE_MIN \
             or z > _UTMUPS_ZONE_MAX \
             or B not in u._Bands:
        t = '%s(%s%s %s)' % (U, z,B, h)
        raise Error(coord=t, zone=zone, band=band, hemisphere=hemi)

    if enMM:
        _en(e, M.eMin[i] - s, M.eMax[i] + s, _easting_)   # PYCHOK .eMax .eMin
        _en(n, M.nMin[i] - s, M.nMax[i] + s, _northing_)  # PYCHOK .nMax .nMin


def utmupsValidateOK(coord, falsed=False, ok=True):
    '''Check a UTM or UPS coordinate.

       @arg coord: The UTM or UPS coordinate (L{Utm}, L{Ups} or C{5+Tuple}).
       @kwarg falsed: C{5+Tuple} easting and northing are falsed (C{bool}).
       @kwarg ok: Result to return if validation passed (B{C{ok}}).

       @return: B{C{ok}} if validation passed, the L{UTMUPSError} otherwise.

       @see: Function L{utmupsValidate}.
    '''
    try:
        utmupsValidate(coord, falsed=falsed)
        return ok
    except UTMUPSError as x:
        return x


def utmupsZoneBand5(lat, lon, cmoff=False):
    '''Return the UTM/UPS zone number, Band letter, hemisphere/pole
       and clipped lat- and longitude for a given location.

       @arg lat: Latitude in degrees (C{scalar} or C{str}).
       @arg lon: Longitude in degrees (C{scalar} or C{str}).
       @kwarg cmoff: Offset longitude from the zone's central
                     meridian, for UTM only (C{bool}).

       @return: A L{UtmUpsLatLon5Tuple}C{(zone, band, hemipole,
                lat, lon)} where C{hemipole} is C{'N'|'S'}, the
                UTM hemisphere or UPS pole, the UPS projection
                top/center.

       @raise RangeError: If B{C{lat}} outside the valid UTM or UPS
                          bands or if B{C{lat}} or B{C{lon}} outside
                          the valid range and L{rangerrors} set to
                          C{True}.

       @raise ValueError: Invalid B{C{lat}} or B{C{lon}}.

       @see: Functions L{utmZoneBand5} and L{upsZoneBand5}.
    '''
    try:
        return utmZoneBand5(lat, lon, cmoff=cmoff)
    except RangeError:
        return upsZoneBand5(lat, lon)

# **) MIT License
#
# Copyright (C) 2016-2020 -- mrJean1 at Gmail -- All Rights Reserved.
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
