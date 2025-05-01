# Based on https://www.gribble.org/cycling/power_v_speed.html

from math import sqrt

import geopy.distance
import gpxpy

# Minimum speed threshold (below this and we're in pain).
PAIN = 6.0   # kph
PAIN_LIMIT = 3.0  # PAIN is usually the speed of pedalling in the easiest gear
                  # at a comfortable cadence, so we can't go much slower.
                  # However, by artificially allowing slower speeds, we can
                  # increase the weight of time spent at the lowest gear to
                  # try to better represent the physical stress of the ride.
                  # PAIN_LIMIT is the minimum of this artificial speed.

# Maximum speed threshold (above this and we don't pedal).
FREE = 40.0  # kph

# These numbers are from nowhereland. :)
POWER = 120  # watts
WEIGHT = 80  # kg (bike + rider)
CDA = 0.5
CRR = 0.008
DTLOSS = 0.05  # fraction

# Other constants.
G = 9.8067
RHO = 1.225  # kg/m^3 (air density) (also this is not constant...)

import sys

with open(sys.argv[1]) as fp:
    gpx = gpxpy.parse(fp)

for track in gpx.tracks:

    # Total distance for the whole track.
    distance = 0

    # Total elevation change for the whole track.
    elevation_gain = 0
    elevation_loss = 0

    # Time estimate for the whole track.
    estimate = 0

    # Pain estimate for whole track (time at min speed).
    pain = 0

    # Freewheel estimate for whole track (time spent at max speed).
    free = 0

    # Time markers to keep myself on track.
    # Format: [(estimate, distance), ... ]
    breakpoints = [(estimate, distance)]
    breakpoint_freq = 3600

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

            velocity = max(PAIN_LIMIT, min(FREE, 3.6 * lo))

            # Update track stats.
            distance += hyp
            elevation_gain += (rise > 0) * rise
            elevation_loss -= (rise < 0) * rise

            duration = 3.6 * hyp / velocity
            estimate += duration
            pain += duration * (velocity <= PAIN)
            free += duration * (velocity == FREE)

            # Update breakpoints if required.
            if estimate >= breakpoints[-1][0] + breakpoint_freq:
                breakpoints.append((estimate, distance))

    print(f'distance: {distance / 1000:.2f}km')
    print(f'elevation gain: {elevation_gain:.0f}m')
    print(f'elevation loss: {elevation_loss:.0f}m')

    print()

    h, m = divmod(estimate // 60, 60)
    print(f'time: {int(h):02}h{int(m):02}m')

    h, m = divmod(pain // 60, 60)
    print(f'pain: {int(h):02}h{int(m):02}m ({100 * pain / estimate:.1f}%)')

    h, m = divmod(free // 60, 60)
    print(f'free: {int(h):02}h{int(m):02}m ({100 * free / estimate:.1f}%)')

    print()

    if estimate != breakpoints[-1][0]:
        breakpoints.append((estimate, distance))

    print('breakpoints:')
    for t, d in breakpoints[1:]:
        h, m = divmod(t // 60, 60)
        print(f'{int(h):02}h{int(m):02}m -- {d / 1000:.2f}km')

    # NOTE currently only investigate the first track
    break
