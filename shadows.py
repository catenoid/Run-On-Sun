import Image
import numpy
import ephem
import datetime

def datetime2azalt(datetime):
  # At datetime, what is the angular location
  # of the sun over the map in radians?
  # azimuthal angle is measured clockwise from north
  # altitude angle is the elevation from the horizon
  o = ephem.Observer()
  o.lat, o.long, o.date = '51:45', '-1:15', datetime
  sun = ephem.Sun(o)
  return float(sun.az), float(sun.alt)

def array2image(array):
  # Converts a numpy array to an image
  normArray = (255.0 / array.max() * (array - array.min())).astype(numpy.uint8)
  im = Image.fromarray(normArray)
  return im

def generateBitmask(buildingMap, datetime, NSamples):
  """A shadow map bitmask represents a map
  that defines whether an object standing at a certain point
  will be shaded by the occulting structure(s) around it.
  """
  # Check the sun is above the horizon
  az, alt = datetime2azalt(datetime)
  if alt <= 0 or alt >= numpy.pi:
    # All shadow
    arrayFile = open('shadowMap_'+str(datetime.hour)+'h.npy', 'w')
    print 'opened for hour ' + str(datetime.hour)
    numpy.save(arrayFile,numpy.zeros((100,100)))
    return
  ground = buildingMap.min()
  shadowMap = numpy.ones((100,100))
  # Check which quadrant we're in
  if numpy.sin(az) > 0:
    azDispl = numpy.array([-1, numpy.cos(az)/numpy.sin(az)])
  elif numpy.sin(az) < 0:
    azDispl = numpy.array([ 1,-numpy.cos(az)/numpy.sin(az)])
  elif numpy.cos(az) > 0:
    azDispl = numpy.array([ 0,-1])
  elif numpy.cos(az) < 0:
    azDispl = numpy.array([ 0, 1])

  altDispl = numpy.tan(alt)
  # generate random numbers on a subset of the image,
  # size is (number of desired samples, 2), representing coords
  randomSample = numpy.random.random_integers(0, 99, (NSamples,2))
  for sample in range(0,NSamples):
    # Array points are used for mathematics
    # Tuple points are used for indexing arrays
    arrayPoint = randomSample[sample]
    tuplePoint = arrayPoint[0],arrayPoint[1]
    shadowH = buildingMap[tuplePoint]
    while(shadowH > ground):
      # Track the shadow across the points it intersects
      # After each step, the shadow shortens
      shadowH -= altDispl
      arrayPoint += azDispl
      # buildingMap must be indexed by a tuple of integers
      tupleinterpolated = int(round(arrayPoint[0])),int(round(arrayPoint[1]))
      if(0<=tupleinterpolated[0]<100 and 0<tupleinterpolated[1]<100): # Check shadow's in range
        if(shadowH > buildingMap[tupleinterpolated]):
          shadowMap[tupleinterpolated] = 0
  arrayFile = open('shadowMap_'+str(datetime.hour)+'h.npy', 'w')
  print 'opened for hour ' + str(datetime.hour)
  numpy.save(arrayFile,shadowMap)
  arrayFile.close()

#heightMap = numpy.load('fromZero.npy')

#for hour in xrange(24):
#  now = datetime.datetime(2014,3,8,hour,0)
#  generateBitmask(heightMap,now,9999)

#bitmaskImage = array2image(shadowMap)
#bitmaskImage.save('shadowMap_Image.png')
