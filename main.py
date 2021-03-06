import math
import numpy
import ephem
import datetime

def datetime2azalt(datetime):
  """At datetime, what is the angular location
  of the sun over the map in radians?
  azimuthal angle is measured clockwise from north
  altitude angle is the elevation from the horizon
  """
  o = ephem.Observer()
  o.lat, o.long, o.date = '51:45', '-1:15', datetime
  sun = ephem.Sun(o)
  return float(sun.az), float(sun.alt)

def azalt2normalVector(az,alt):
  """turn the two angles into a cartesian vector"""
  x =  numpy.cos(alt)*numpy.sin(az)
  y =  numpy.sin(alt)
  z = -numpy.cos(alt)*numpy.cos(az)
  return numpy.array([x,y,z])

def irradianceScaled(sunV,datetime):
  # Gave up trying to find real hourly insolation data for this latitude
  # AFAIK, three kinds of solar irradiance data: global, direct and diffuse
  return sunV * 0.5 *(1 - numpy.cos((2*numpy.pi*datetime.hour)/ 24))

def makeArray(filename):
  """Converts space delimited height data into a numpy array"""
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

def smoothedCrossProduct(i,j,inter):
  # Now makes 8 vectors
  # Once halved, vector magnitude is area of triangle
  one = 0.5*numpy.array([inter[1]-inter[0],1,inter[0]-inter[3]])
  two = 0.5*numpy.array([inter[3]-inter[4],1,inter[1]-inter[4]])
  thr = 0.5*numpy.array([inter[2]-inter[1],1,inter[1]-inter[4]])
  fou = 0.5*numpy.array([inter[4]-inter[5],1,inter[2]-inter[5]])
  fiv = 0.5*numpy.array([inter[4]-inter[3],1,inter[3]-inter[6]])
  six = 0.5*numpy.array([inter[6]-inter[7],1,inter[4]-inter[7]])
  sev = 0.5*numpy.array([inter[5]-inter[4],1,inter[4]-inter[7]])
  eig = 0.5*numpy.array([inter[7]-inter[8],1,inter[5]-inter[8]])
  return (one,two,thr,fou,fiv,six,sev,eig)

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

def makeSmoothedNormalVectorArray(A):
  smoothedNormalVectorArray = numpy.zeros((100,100,4,2,3))
  #m, n = A.shape
  for i in xrange(100):
    for j in xrange(100):
      inter = [A[i,j],
               0.5*(A[i+1,j]+A[i,j]),
               A[i+1,j],
               0.5*(A[i,j+1]+A[i,j]),
               0.25*(A[i,j]+A[i+1,j]+A[i,j+1]+A[i+1,j+1]),
               0.5*(A[i+1,j+1]+A[i+1,j]),
               A[i,j+1],
               0.5*(A[i,j+1]+A[i+1,j+1]),
               A[i+1,j+1]]
      for quad in xrange(4):
        for k in (0,1):
          for l in (0,1,2):
            smoothedNormalVectorArray[i,j,quad,k,l] = smoothedCrossProduct(i,j,inter)[2*quad+k][l]
  arrayFile = open('smoothedNormalVectorArray.npy', 'w')
  numpy.save(arrayFile,smoothedNormalVectorArray)

def shaderArray(A,sunV):
  # dot each normal vector with the averaged sun vector
  #m, n = A.shape[0],A.shape[1]
  scalarArray = numpy.zeros((100,100,2))
  for i in xrange(100):
    for j in xrange(100):
      for k in (0,1):
        scalarArray[i,j,k] = max(0,dotProduct(sunV,A[i,j,k]))
  arrayFile = open('scalarArray.npy', 'w')
  numpy.save(arrayFile,scalarArray)

def smoothedShaderArray(A,sunV):
  smoothedScalarArray = numpy.zeros((100,100,4,2))
  for i in xrange(100):
    for j in xrange(100):
      for quad in xrange(4):
        for k in (0,1):
          smoothedScalarArray[i,j,quad,k] = float(max(0,numpy.dot(sunV,A[i,j,quad,k])))
  arrayFile = open('smoothedScalarArray.npy', 'w')
  numpy.save(arrayFile,smoothedScalarArray)
  
def updateShaderArray(A,shaderMap,shadowMap,sunV):
  # dot each normal vector with sun vector and accumulate
  #m, n = A.shape[0],A.shape[1]
  for i in xrange(100):
    for j in xrange(100):
      if shadowMap[i,j] != 0:
        for quad in xrange(4):
          for k in (0,1):
            shaderMap[i,j,quad,k] += float(max(0,numpy.dot(sunV,A[i,j,quad,k])))
  return shaderMap

def normaliseArray(A):
  minimum = A.min()
  maximum = A.max()
  return (A - minimum)/(maximum - minimum)

def hourAverage(smoothedNormalVectorMap,scalarArray):
  for hour in xrange(24):
    now = datetime.datetime(2014,3,8,hour,0)
    unscaledSun = azalt2normalVector(*datetime2azalt(now))
    # Direct radiation exposure
    sun = 0.85 * irradianceScaled(unscaledSun,now)
    shadowMap = numpy.load('shadowMap_'+str(hour)+'h.npy')
    scalarArray = updateShaderArray(smoothedNormalVectorMap,scalarArray,shadowMap,sun)
    # Diffuse radiation exposure
    scalarArray += 0.15 * numpy.linalg.norm(irradianceScaled(unscaledSun,now)) 
  return normaliseArray(scalarArray)

def RGB(value):
  if value > 1:
    print 'Warning, value > 1'
    return '1.f,0.f,0.f' # red
  elif value == 1:
    return '1.f,0.f,0.f' # red 
  elif value < 0:
    print 'Warning, value < 0'
    return '0.f,0.f,1.f' # blue

  # blue, cyan, green, yellow, red with linear interpolation
  # Serious outlier problem here, causing almost all values to fall between the first 2 colours
  colours =[[0,0,1],[0,1,1],[0,1,0],[1,1,0],[1,0,0],[1,0,0]]
  N = len(colours)
  lower = math.floor(value*(N-1))
  f = value*(N-1) - lower
  first = int(lower)
 
  r = float(f*(colours[first+1][0]-colours[first][0])+colours[first][0])
  g = float(f*(colours[first+1][1]-colours[first][1])+colours[first][1])
  b = float(f*(colours[first+1][2]-colours[first][2])+colours[first][2])
  return '%(red)sf,%(green)sf,%(blue)sf' % {'red':r,'green':g,'blue':b}

def trianglePair(i,j,A,shades):
  # Upper left corner of the bounding square is at coordinate (i,j
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

def triangleOctuple(i,j,A,shades):
  # Upper left corner of the bounding square is at coordinate (i,j)
  # height array m by n (called A)
  # shades array m by n by FOUR [subdivition] by 2
  # interpolated: specifies points in 3 by 3 raster
  inter = [A[i,j],
           0.5*(A[i+1,j]+A[i,j]),
           A[i+1,j],
           0.5*(A[i,j+1]+A[i,j]),
           0.25*(A[i,j]+A[i+1,j]+A[i,j+1]+A[i+1,j+1]),
           0.5*(A[i+1,j+1]+A[i+1,j]),
           A[i,j+1],
           0.5*(A[i,j+1]+A[i+1,j+1]),
           A[i+1,j+1]]
  OpenGLString = ('glBegin(GL_TRIANGLES);',
                  'glColor3f(%(RGB)s);' %{'RGB':RGB(shades[i,j,0,0])},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i,'y':j,'A':inter[0]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j,'A':inter[1]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i,'y':j+0.5,'A':inter[3]},
                  'glEnd();',
                  'glBegin(GL_TRIANGLES);',
                  'glColor3f(%(RGB)s);' %{'RGB':RGB(shades[i,j,0,1])},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j,'A':inter[1]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j+0.5,'A':inter[4]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i,'y':j+0.5,'A':inter[3]},
                  'glEnd();',

                  'glBegin(GL_TRIANGLES);',
                  'glColor3f(%(RGB)s);' %{'RGB':RGB(shades[i,j,1,0])},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j,'A':inter[1]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+1,'y':j,'A':inter[2]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j+0.5,'A':inter[4]},
                  'glEnd();',
                  'glBegin(GL_TRIANGLES);',
                  'glColor3f(%(RGB)s);' %{'RGB':RGB(shades[i,j,1,1])},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+1,'y':j,'A':inter[2]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+1,'y':j+0.5,'A':inter[5]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j+0.5,'A':inter[4]},
                  'glEnd();',
                  
                  'glBegin(GL_TRIANGLES);',
                  'glColor3f(%(RGB)s);' %{'RGB':RGB(shades[i,j,2,0])},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i,'y':j+0.5,'A':inter[3]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j+0.5,'A':inter[4]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i,'y':j+1,'A':inter[6]},
                  'glEnd();',
                  'glBegin(GL_TRIANGLES);',
                  'glColor3f(%(RGB)s);' %{'RGB':RGB(shades[i,j,2,1])},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j+0.5,'A':inter[4]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j+1,'A':inter[7]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i,'y':j+1,'A':inter[6]},
                  'glEnd();',
                  
                  'glBegin(GL_TRIANGLES);',
                  'glColor3f(%(RGB)s);' %{'RGB':RGB(shades[i,j,3,0])},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j+0.5,'A':inter[4]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+1,'y':j+0.5,'A':inter[5]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j+1,'A':inter[7]},
                  'glEnd();',
                  'glBegin(GL_TRIANGLES);',
                  'glColor3f(%(RGB)s);' %{'RGB':RGB(shades[i,j,3,1])},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+1,'y':j+0.5,'A':inter[5]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+1,'y':j+1,'A':inter[8]},
                  'glVertex3f(%(x)s,%(A)s,%(y)s);' %{'x':i+0.5,'y':j+1,'A':inter[7]},
                  'glEnd();')
  return "\n".join(OpenGLString)

## Alternate method. Instead of using the >0DP, mask with the shadow map
## That way, can use the average sun vector, so do not need to do hourly simulations
## Actually, the above is false.

def maskShadows(shadowMap, shaderMap):
  # shaderMap M by N by 4 by 2
  # shadowMap M by N, 0 is shaded, 1 is unshaded
  # This just turns triangles blue that are shaded
  for i in xrange(1,98):
    for j in xrange(1,98):
      if shadowMap[i,j] == 0:
        shaderMap[i-1,j-1,3,0] = 0
        shaderMap[i-1,j-1,3,1] = 0
        shaderMap[i  ,j-1,2,0] = 0
        shaderMap[i  ,j-1,2,1] = 0
        shaderMap[i-1,j  ,1,0] = 0
        shaderMap[i-1,j  ,1,1] = 0
        shaderMap[i  ,j  ,0,0] = 0
        shaderMap[i  ,j  ,0,1] = 0
  return shaderMap

def generateGL(A,shades):
  # Extend to each box in the grid
  # restricted domain. For the full extent, replace 10 with m,n
  m, n = A.shape
  string = ''
  for i in xrange(70):
    for j in xrange(70):
      string = string + triangleOctuple(i,j,A,shades) # replace with tripair
  return string

def generateGLUT(A,shades):
  # Camera movement, ground etc.
  data = open('template.c', 'r').read() % {'triangulate':generateGL(A,shades)}
  outfile = open('current.c', 'w')
  outfile.write(data)
  outfile.close()

heightMap = numpy.load('fromZero.npy')

#makeSmoothedNormalVectorArray(heightMap)
smoothedNormalVectorMap = numpy.load('smoothedNormalVectorArray.npy')

emptyArray = numpy.zeros((100,100,4,2))
hourAvArray = 10*hourAverage(smoothedNormalVectorMap,emptyArray)

generateGLUT(heightMap,hourAvArray)
