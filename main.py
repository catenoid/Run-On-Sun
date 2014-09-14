# main.py

import numpy
import ephem
import datetime

#import matplotlib.cm
#import matplotlib.colors
#CMAP = 'nipy_spectral'

def datetime2azalt(datetime):
  # At datetime, what is the angular location
  # of the sun over the map in radians?
  # azimuthal angle is measured clockwise from north
  # altitude angle is the elevation from the horizon
  o = ephem.Observer()
  o.lat, o.long, o.date = '51:45', '-1:15', datetime
  sun = ephem.Sun(o)
  return float(sun.az), float(sun.alt)

def azalt2normalVector(az,alt):
  # turn the two angles into a cartesian vector
  x =  numpy.cos(alt)*numpy.sin(az)
  y =  numpy.sin(alt)
  z = -numpy.cos(alt)*numpy.cos(az)
  return numpy.array([x,y,z])

def makeArray(filename):
  # Extract what we want from the GIS file
  # filename = 'SP5106_DSM_1M.asc'
  data = open(filename, 'r')
  print "Opened file"
  #parameters = dict()
  heightmap = []
  print "Building array"
  for line in data:
    if not line[0].isdigit():
      # parse the parameters; ncols, nrows etc.
      # parameters[line.split(' ')[0]] = line[14:]
      continue
    # For the space-delimited numeric data
    heightmap.append(line.split(' ')[:-1])
    buildingMap = numpy.array(heightmap).astype(float)
  print "Array done"
  arrayFile = open('numpyarray.npy', 'w')
  numpy.save(arrayFile,buildingMap)
  return buildingMap

def crossProduct(i,j,A):
  # normal vector for two triangles, upper and lower
  # by referencing the array and dividing by vector length
  # i,j indexes the upper left corner of the bounding square
  # 2 by 3 array
  one = numpy.array([A[i+1,j]-A[i,j],1,A[i,j]-A[i,j+1]])
  two = numpy.array([A[i,j+1]-A[i+1,j+1],1,A[i+1,j]-A[i+1,j+1]])
  normalOne = normalised(one)
  normalTwo = normalised(two)
  return (normalOne, normalTwo)

def normalised(vector):
  return vector / numpy.linalg.norm(vector)

def makeNormalVectorArray(A):
  # 4 dimensional array, m by n by 2 by 3
  # each point is associated with two normal vectors
  # each vector is of three components
  normalVectorArray = numpy.zeros((100,100,2,3))
  #m, n = A.shape
  for i in xrange(100):
    for j in xrange(100):
      for k in (0,1):
        for l in (0,1,2):
          normalVectorArray[i,j,k,l] = crossProduct(i,j,A)[k][l]
  arrayFile = open('normalVectorArray.npy', 'w')
  numpy.save(arrayFile,normalVectorArray)

def dotProduct(one,two):
  # computes a dot product
  # in context, between a triangle's normal vector
  # and the sun ray vector
  return numpy.dot(one,two)

def shaderArray(A,sunV):
  # dot each normal vector with the sun vector
  # insert this scaler where the normal vector once was
  scalarArray = numpy.zeros((100,100,2))
  #m, n = A.shape[0],A.shape[1]
  for i in xrange(100):
    for j in xrange(100):
      for k in (0,1):
          scalarArray[i,j,k] = max(0,dotProduct(sunV,A[i,j,k]))
  arrayFile = open('scalarArray.npy', 'w')
  numpy.save(arrayFile,scalarArray)

# Under construction: New heatmap
#norm = matplotlib.colors.Normalize(vmin=0, vmax=1, clip=False)
#smap = matplotlib.cm.ScalarMappable(norm, CMAP)
#def matplotlibRGB(value):
#  r, g, b, alpha = smap.to_rgba(value, alpha=None, bytes=True)
#  return '%(red)s,%(green)s,%(blue)s' % {'red':r,'green':g,'blue':b} 

def RGB(value):
  # From a normalised shade zero to one, convert to RGB with linear interpolation
  # in this case, zero is blue (cold) and one is red (hot)
  b = max(0, (1 - 2*value))
  r = max(0, (2*value - 1))
  g = 1 - b - r
  return '%(red)s,%(green)s,%(blue)s' % {'red':r,'green':g,'blue':b}

def trianglePair(i,j,A,shades):
  # Upper left corner of the bounding square is at coordinate (i,j)
  # height array m by n (called A)
  # shades array m by n by 2
  OpenGLString = ('glBegin(GL_TRIANGLES);',
                  'glColor3f(%(RGB)s);' %{'RGB':RGB(shades[i,j,0])},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i,'y':j,'A':A[i,j]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+1,'y':j,'A':A[i+1,j]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i,'y':j+1,'A':A[i,j+1]},
                  'glEnd();',
                  'glBegin(GL_TRIANGLES);',
                  'glColor3f(%(RGB)s);' %{'RGB':RGB(shades[i,j,1])},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+1,'y':j,'A':A[i+1,j]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+1,'y':j+1,'A':A[i+1,j+1]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i,'y':j+1,'A':A[i,j+1]},
                  'glEnd();') 
  return "\n".join(OpenGLString)

def generateGL(A,shades):
  # Extend to each box in the grid
  # restricted domain. For the full extent, replace 10 with m,n
  m, n = A.shape
  string = ''
  for i in xrange(100):
    for j in xrange(100):
      string = string + trianglePair(i,j,A,shades)
  return string

def generateGLUT(A,shades):
  # Camera movement, ground etc.
  data = open('template.c', 'r').read() % {'triangulate':generateGL(A,shades)}
  outfile = open('current.c', 'w')
  outfile.write(data)
  outfile.close()

heightMap = numpy.load('fromZero.npy')
sample_datetime = datetime.datetime(2014,3,8,10,0)
sunV = azalt2normalVector(*datetime2azalt(sample_datetime))

makeNormalVectorArray(heightMap)
normalVectorMap = numpy.load('normalVectorArray.npy')

shaderArray(normalVectorMap,sunV)
shaderMap = numpy.load('scalarArray.npy')

generateGLUT(heightMap,shaderMap)
