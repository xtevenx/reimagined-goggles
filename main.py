# Based on https://www.gribble.org/cycling/power_v_speed.html

from math import sqrt

import geopy.distance
import gpxpy

# Minimum speed threshold (below this and we're in pain).
PAIN = 7.0  # kph

# These numbers are from nowhereland. :)
POWER = 120  # watts
WEIGHT = 80  # kg (bike + rider)
CDA = 0.5
CRR = 0.008
DTLOSS = 0.05  # fraction

# Other constants.
G = 9.8067
RHO = 1.225  # kg/m^3 (air density)

import sys

with open(sys.argv[1]) as fp:
    gpx = gpxpy.parse(fp)

for track in gpx.tracks:

    # Total distance for the whole track.
    distance = 0

    # Time estimate for the whole track.
    estimate = 0

    # Pain estimate for whole track (time at min speed).
    pain = 0

    for segment in track.segments:
        for i, pnt in enumerate(segment.points[:-1]):
            nxt = segment.points[i + 1]

            rise = nxt.elevation - pnt.elevation

            # NOTE this calculation assumes we're at sea level, so may (very)
            # slightly underestimate the distance.
            run = geopy.distance.geodesic((pnt.latitude, pnt.longitude),
                                          (nxt.latitude, nxt.longitude)).meters

            # Sometimes there are issues...
            if not (hyp := sqrt(rise**2 + run**2)):
                continue

            # Solve the cubic for the largest real root.
            a = 0.5 * CDA * RHO
            c = G * WEIGHT * (rise / hyp + CRR * run / hyp)
            d = -(1 - DTLOSS) * POWER

            def p(x):
                return a * x**3 + c * x + d

            lo = -1e8 if (s := -c / (3 * a)) < 0 else sqrt(s)
            hi = 1e8
            while hi - lo > 1e-8:
                mid = (hi + lo) / 2
                if p(mid) < 0:
                    lo = mid
                else:
                    hi = mid

            velocity = max(PAIN, 3.6 * lo)

            # Update track stats.
            distance += hyp

            duration = 3.6 * hyp / velocity
            estimate += duration
            pain += duration * (velocity == PAIN)

    print(f'distance: {distance / 1000:.2f}km')

    h, m = divmod(estimate // 60, 60)
    print(f'time: {int(h):02}h{int(m):02}m')

    h, m = divmod(pain // 60, 60)
    print(f'pain: {int(h):02}h{int(m):02}m')

    # NOTE currently only investigate the first track
    break
