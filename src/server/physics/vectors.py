import math
import operator

DEBUG = True

class DimensionalityError(Exception): pass

class Vector(object):
  """N-dimensional vector of arbitrary units."""

  def __init__(self, *dimensions):
    self.dimensions = tuple(map(float, dimensions))

    # Store an iterator.
    self.iter_count = 0

  def dimensionality(self):
    """Return the number of dimensions the vector represents."""
    return len(self.dimensions)

  def magnitude(self):
    """Calculate the magniture of the vector."""
    return math.sqrt(sum((n**2 for n in self.dimensions)))

  def norm(self):
    """Calculate the unit vector of the same dimensionality."""
    mag = self.magnitude()

    # Note that we do some strange things with types and arguments here,
    # so that we automatically construct more specific subclasses, if
    # appropriate.
    return type(self)(*[n/mag for n in self.dimensions])

  def dot(self, nvec):
    """Calculate the dot product of two vectors of the same
dimensionality"""
    if self.dimensionality() != nvec.dimensionality():
      raise DimensionalityError(
          "cannot perform operation on vectors %s and %s"
          % (self, nvec))

    # Iterate through each set of dimensions, as (x1, x2), (y1, y2),
    # etc.
    return sum((n1 * n2 for n1, n2 in zip(self.dimensions,
      nvec.dimensions)))

  def __getitem__(self, key):
    """Return the dimesion given by key when used in a slice notation"""
    return self.dimensions[key]

  def __bool__(self):
    """Evaluate to True if the vector is nonzero in any dimension."""
    # Generate a list of truth values for every element in the
    # dimensionality. (0 values are False, others are True). If any of
    # these are True, then the vector is True.
    return any(map(bool, self.dimensions))

  def __eq__(self, nvec):
    """Test equality between two vectors."""
    if hasattr(nvec, "dimensions"):
        return self.dimensions == nvec.dimensions
    else:
        return self.dimensions == list(nvec)

  def __neg__(self):
    """Negate the vector."""

    # Preserve the type and dimensionality.
    return type(self)(*[-n for n in self.dimensions])

  def __add__(self, rhs):
    """Add two vectors."""
    # This operation is only defined for two vectors, so we can just
    # pass it to _op_by_dimension_, assuming it's a vector.
    if not issubclass(type(rhs), Vector): return NotImplemented

    return self._op_by_dimension_(operator.add, self, rhs)

  def __sub__(self, rhs):
    """Subtract one vector from another."""
    # Again, this is only valid for two vectors.
    if not issubclass(type(rhs), Vector): return NotImplemented

    return self._op_by_dimension_(operator.sub, self, rhs)

  def __mul__(self, rhs):
    """Multiply one vector and one scalar, or two vectors."""
    # First, check if the right hand side is a vector. If so, pass it to
    # _op_by_dimension_.
    if issubclass(type(rhs), Vector):
      return self._op_by_dimension_(operator.mul, self, rhs)

    # Otherwise, use the scalar.
    else:
      # Preserve the type and dimensionality.
      return type(self)(*[n1 * rhs for n1 in self.dimensions])

  def __rmul__(self, lhs):
    """Calls multiply."""
    return self * lhs

  def __floordiv__(self, rhs):
    """Divide one vector by a scalar, or two vectors using floor
division."""
    if issubclass(type(rhs), Vector):
      return self._op_by_dimension_(operator.floordiv, self, rhs)

    else:
      return type(self)(*[n1 // rhs for n1 in self.dimensions])

  def __truediv__(self, rhs):
    """Divide one vector by a scalar, or two vectors using true
division."""
    if issubclass(type(rhs), Vector):
      return self._op_by_dimension_(operator.truediv, self, rhs)

    else:
      return type(self)(*[n1 / rhs for n1 in self.dimensions])

  @classmethod
  def _op_by_dimension_(cls, op, nvec1, nvec2):
    """Apply an operator, element by element, to two Vectors. If they
are of different dimensionalities, raise a DimensionalityError."""

    if nvec1.dimensionality() != nvec2.dimensionality():
      raise DimensionalityError("cannot perform operation on vectors \
%s and %s" % (nvec1, nvec2))

    return cls(*[op(n1, n2) for n1, n2 in zip(nvec1.dimensions,
      nvec2.dimensions)])

  def __iter__(self):
    return self

  def __next__(self):
    try:
      c = self.iter_count
      self.iter_count += 1
      return self.dimensions[c]
    except IndexError:
      raise StopIteration

  def __str__(self):
    return "<" + ", ".join(("%f" % n for n in self.dimensions)) + ">"

  def __repr__(self):
    return "'%s'" % str(self)

class TriVector(Vector):
  """Three dimensional vector of arbitrary units."""
  def __init__(self, x = 0, y = 0, z = 0):
    self.x, self.y, self.z = float(x), float(y), float(z)
    self.dimensions = self.x, self.y, self.z

    self.iter_count = 0

  def cross(self, vec):
    """Calculate the cross product of two 3-vectors."""
    x1, y1, z1 = self.dimensions
    x2, y2, z2 = vec.dimensions
    return Vector(y1 * z2 - z1 * y2, z1 * x2 - x1 * z2,
        x1 * y2 - y1 * x2)

def VectorMultiply(scalar, vector):
  result = [0] * len(vector)
  for i in range(len(vector)):
    result[i] = scalar * vector[i]
  return result

def VectorAdd(a, b):
  assert len(a) == len(b), "Attempted to add two vectors of different lengths: %s vs %s" % (len(a), len(b))
  c = [0] * len(b)
  for i in range(len(b)):
    c[i] = a[i] + b[i]
  return c

def Dot(a,b):
  """Dot returns the dot product of two vectors. The vectors must be of the same length, or else Dot will return 0."""
  assert len(a) == len(b), "Dot was given vectors of diffrent lengths. a: %s b: %s" % (a, b)
  c = 0
  for i in range(len(a)):
    c = c + a[i] * b[i]
  return c

def Cross(a,b):
  """Cross returns the cross product of 2 vectors of length 3, or a zero vector if the vectors are not both length 3."""
  assert len(a) == len(b) == 3, "Cross was given a vector whose length is not 3. a: %s b: %s" % (a, b)
  c = [a[1]*b[2] - a[2]*b[1], a[2]*b[0] - a[0]*b[2], a[0]*b[1] - a[1]*b[0]]
  return c

def Normalize(a): 
  """Normalize returns a normalized vector.  It will complain in debug-mode when given a zero-vector."""
  s = 0
  c = [0] * len(a)
  s = Dot(a, a)
  s = math.sqrt(s)
  if s == 0:
    if DEBUG:
      print("Normalize was given a zero vector. This is not necessarily an error; returning zero vector.")
    return c
  for i in range(len(a)):
    c[i] = a[i]/s
  return c

def Magnitude(a):
  """Magnitude returns the square root of the sum of the numbers of a list squared."""
  c = 0
  for i in range(len(a)):
    c = c + a[i]**2
  return math.sqrt(c)

def Distance(a, b):
  """Distance returns the distance between two vectors of length 3."""
  assert len(a) == len(b) == 3, "Distance was given vectors whose lengths are not both 3."
  c = (a[0]-b[0])**2 + (a[1]-b[1])**2 + (a[2]-b[2])**2
  return math.sqrt(c)

def Angle(a,b):
  cos=Dot(Normalize(a),Normalize(b))
  if cos > 1:
    cos = 1
  if cos < -1:
    cos = -1
  return math.acos(cos)

def AngleVectorToQuaternion(angle, vector):
  normvector = Normalize(list(vector))
  angle = angle/2
  quaternion = [math.cos(angle), math.sin(angle)*normvector[0], math.sin(angle)*normvector[1], math.sin(angle)*normvector[2]]
  return Normalize(quaternion)

def OrientationQuaternion(location, target, referenceOrientation):
  reference = Normalize(referenceOrientation)
  facing = [0,0,0]
  for i in range(3):
    facing[i] = target[i] - location[i]
  if Magnitude(facing) == 0:
    return [1,0,0,0]
  perpendicular = Cross(reference, facing)
  angle = Angle(reference, facing)
  quaternion = AngleVectorToQuaternion(angle, perpendicular)
  return quaternion

def QuaternionMultiply(apoint, bpoint):
  a = list(apoint)
  b = list(bpoint)
  if len(a) == 3:
    a = [0, a[0], a[1], a[2]]
  if len(b) == 3:
    b = [0, b[0], b[1], b[2]]
  assert len(a) == len(b) == 4, "QuaternionMultiply was given lists of the wrong length: %s * %s" % (a, b)
  result = [0,0,0,0]
  result[0] = a[0]*b[0] - a[1]*b[1] - a[2]*b[2] - a[3]*b[3]
  result[1] = a[0]*b[1] + a[1]*b[0] + a[2]*b[3] - a[3]*b[2]
  result[2] = a[0]*b[2] + a[2]*b[0] + a[3]*b[1] - a[1]*b[3]
  result[3] = a[0]*b[3] + a[3]*b[0] + a[1]*b[2] - a[2]*b[1]
  return result

def RotateVectorByQuaternion(vectorpoint, quaternionpoint):
  vector = list(vectorpoint)
  quaternion = Normalize(list(quaternionpoint))
  inversequaternion = [quaternion[0], -quaternion[1], -quaternion[2], -quaternion[3]]
  result = QuaternionMultiply(QuaternionMultiply(quaternion, vector), inversequaternion)
  vectorresult = [result[1], result[2], result[3]]
  if math.fabs(result[0]) > 10 ** (-15):
    if DEBUG:
      print("RotateVectorByQuaternion gave a non-zero real result for", vector, quaternion)
  return vectorresult

def RotateQuaternionByQuaternion(apoint, bpoint):
  a = Normalize(list(apoint))
  b = Normalize(list(bpoint))
  inverseb = [b[0], -b[1], -b[2], -b[3]]
  result = QuaternionMultiply(QuaternionMultiply(b, a), inverseb)
  return result

def TurnTowards(rotationpoint, locationpoint, targetLocationpoint, turning, referenceOrientation, timeMultiplier):
  facing = OrientatioVector(list(rotationpoint), referenceOrientation)
  rotation = list(rotationpoint)
  location = list(locationpoint)
  targetLocation = list(targetLocationpoint)
  targetFacing = [0,0,0]
  for i in range(3):
    targetFacing[i] = targetLocation[i] - location[i]
  if Magnitude(targetFacing) == 0:
    return rotation
  perpendicular = Cross(facing, targetFacing)
  angle = Angle(facing, targetFacing)
  if angle > timeMultiplier * .4 * turning:
    angle = timeMultiplier * .4 * turning
  if angle < -timeMultiplier * .4 * turning:
    angle = -timeMultiplier * .4 * turning
  rotationQuaternion = AngleVectorToQuaternion(angle, perpendicular)
  result = RotateQuaternionByQuaternion(rotation, rotationQuaternion)
  return result

def DerollFacing(quaternionpoint): #doesn't work yet
  q = Normalize(list(quaternionpoint))
  roll  = math.atan2(2*q[2]*q[0] - 2*q[1]*q[3], 1 - 2*q[2]*q[2] - 2*q[3]*q[3])
  vector = Normalize(OrientatioVector(q))
  derolled = RotateQuaternionByQuaternion(AngleVectorToQuaternion(-1 * roll, vector),q)
  return derolled
  
def CheckRoll(quaternionpoint):
  q = list(quaternionpoint)
  roll  = atan2(2*q[2]*q[0] - 2*q[1]*q[3], 1 - 2*q[2]*q[2] - 2*q[3]*q[3])
  return roll

def OrientatioVector(quaternionpoint, referenceOrientation):
  quaternion = list(quaternionpoint)
  reference = Normalize(referenceOrientation)
  return RotateVectorByQuaternion(reference, quaternion)
