import numpy as np

from typing import Iterable, Iterator, List, Optional, Union, SupportsIndex, overload
from typing_extensions import Self


class Vec2:
    """
    2D vector class.
    Includes an optional z component for extra data storage.
    But all operations are done in 2D.
    """
    def __init__(self, x: float = 0.0, y: float = 0.0, z: float = 0.0, 
                 data: Optional[np.ndarray] = None) -> None:
        """ 2D vector with optional z component for extra data storage. """
        if data is not None:
            if data.shape[0] == 3:
                self._data = data  # If it's 3D, keep as is
            else:
                self._data = np.array([x, y, z], dtype=np.float32)
                self._data[0:data.shape[0]] = data  # Insert provided data
        else:
            self._data = np.array([x, y, z], dtype=np.float32)
        
        self._vector = self._data[0:2]

    @property
    def x(self) -> float:
        return self._data[0]
  
    @x.setter
    def x(self, value: float) -> None:
        self._data[0] = value
  
    @property
    def y(self) -> float:
        return self._data[1]

    @y.setter
    def y(self, value: float) -> None:
        self._data[1] = value

    @property
    def z(self) -> float:
        return self._data[2]
  
    @z.setter
    def z(self, value: float) -> None:
        self._data[2] = value

    def translate(self, vector: Self):
        """ Translates the vector by another vector. """
        self._data += vector._data

    def translated(self, vector: Self) -> Self:
        """ Returns a new vector that is the translation of this vector by another vector. """
        return Vec2(data=self._data + vector._data)

    def rotate(self, direction: Self):
        """ Rotates the vector by another vector (direction). """
        dx, dy = direction.normalised()
        if dx == 0 and dy == 0:
            return
        right_x = -dy
        right_y = dx
        self._vector[0] = self.x * right_x + self.y * dx
        self._vector[1] = self.x * right_y + self.y * dy

    def rotated(self, direction: Self) -> Self:
        """ Returns a new vector that is the rotation of this vector by another vector (direction). """
        dx, dy = direction.normalised()
        if dx == 0 and dy == 0:
            return Vec2(data=self._data.copy())
        right_x = -dy
        right_y = dx
        return Vec2(self.x * right_x + self.y * dx, self.x * right_y + self.y * dy, self.z)
        # return Vec2(self.y * dx + self.x * dy, -self.x * dx + self.y * dy, self.z)
    
    def rotate_angle(self, angle: float, degrees: bool = True):
        """ Rotates the vector by the given angle in place. """
        if degrees:
            angle = np.radians(angle)
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        x = self.x * cos_a - self.y * sin_a
        y = self.x * sin_a + self.y * cos_a
        self._vector[0] = x
        self._vector[1] = y
    
    def rotated_angle(self, angle: float, degrees: bool = True) -> Self:
        """ Returns a new vector that is this vector rotated by the given angle. """
        if degrees:
            angle = np.radians(angle)
        cos_a = np.cos(angle)
        sin_a = np.sin(angle)
        x = self.x * cos_a - self.y * sin_a
        y = self.x * sin_a + self.y * cos_a
        return Vec2(x, y, self.z)

    def rotate_90(self, count: int = 1):
        """ Rotates this vector 90 degrees clockwise 'count' times in place. """
        x, y = self._vector
        count = count % 4
        if count == 0:
            return
        elif count == 1:
            self._vector[0] = y
            self._vector[1] = -x
        elif count == 2:
            self._vector[0] = -x
            self._vector[1] = -y
        else:  # count == 3
            self._vector[0] = -y
            self._vector[1] = x

    def rotated_90(self, count: int = 1) -> Self:
        """ Returns a new vector that is this vector rotated 90 degrees clockwise 'count' times. """
        x, y = self._vector
        count = count % 4
        if count == 0:
            return Vec2(x, y, self.z)
        elif count == 1:
            return Vec2(y, -x, self.z)
        elif count == 2:
            return Vec2(-x, -y, self.z)
        else:  # count == 3
            return Vec2(-y, x, self.z)
    
    def to_degrees(self) -> float:
        """ Returns the angle of the vector in degrees from the positive x-axis. """
        return float(np.degrees(np.arctan2(self.x, self.y)))  # (x, y) for 0, 1 to be 0 degrees

    def magnitude(self) -> float:
        return float(np.linalg.norm(self._vector))
  
    def normalise(self):
        """ Normalises the vector in place. """
        mag = self.magnitude()
        if mag > 0:
            self._vector /= mag

    def normalised(self) -> Self:
        """ Returns a new normalised vector. """
        mag = self.magnitude()
        if mag > 0:
            x, y = self._vector / mag
            return Vec2(x, y, self.z)
        return Vec2(data=self._data.copy())
    
    def clone(self) -> Self:
        """ Returns a copy of the vector. """
        return Vec2(data=self._data.copy())
    
    def cross(self, other: Self) -> float:
        """ Returns the 2D cross product (scalar) of this vector and another. """
        return self.x * other.y - self.y * other.x

    def dot(self, other: Self) -> float:
        """ Returns the dot product of this vector and another. """
        return float(np.dot(self._vector, other._vector))

    def __len__(self) -> int:
        return 2

    @overload
    def __getitem__(self, index: slice) -> np.ndarray: ...
    @overload
    def __getitem__(self, index: int) -> float: ...

    def __getitem__(self, index: SupportsIndex) -> Union[float, np.ndarray]:
        return self._data[index]
  
    @overload
    def __setitem__(self, index: slice, value: np.ndarray) -> None: ...
    @overload
    def __setitem__(self, index: int, value: float) -> None: ...

    def __setitem__(self, index: SupportsIndex, value: Union[float, np.ndarray]) -> None:
        self._data[index] = value

    # ---- Operators ----
    # Ignores z for these operations since it's realistatically not used in them

    def __add__(self, value: Union[float, Self, np.ndarray]) -> Self:
        if isinstance(value, Vec2):
            value = value._vector
        x, y = self._vector + value
        return Vec2(x, y, self.z)

    def __iadd__(self, value: Union[float, Self, np.ndarray]) -> Self:
        if isinstance(value, Vec2):
            value = value._vector
        self._vector += value
        return self
  
    def __sub__(self, value: Union[float, Self, np.ndarray]) -> Self:
        if isinstance(value, Vec2):
            value = value._vector
        x, y = self._vector - value
        return Vec2(x, y, self.z)

    def __isub__(self, value: Union[float, Self, np.ndarray]) -> Self:
        if isinstance(value, Vec2):
            value = value._vector
        self._vector -= value
        return self

    def __mul__(self, value: Union[float, Self, np.ndarray]) -> Self:
        if isinstance(value, Vec2):
            value = value._vector
        x, y = self._vector * value
        return Vec2(x, y, self.z)

    def __imul__(self, value: Union[float, Self, np.ndarray]) -> Self:
        if isinstance(value, Vec2):
            value = value._vector
        self._vector *= value
        return self

    def __truediv__(self, value: Union[float, Self, np.ndarray]) -> Self:
        if isinstance(value, Vec2):
            value = value._vector
        x, y = self._vector / value
        return Vec2(x, y, self.z)

    def __itruediv__(self, value: Union[float, Self, np.ndarray]) -> Self:
        if isinstance(value, Vec2):
            value = value._vector
        self._vector /= value
        return self

    def __iter__(self) -> Iterator[float]:
        yield from self._vector

    def __repr__(self) -> str:
        return f"Vec2(x={self.x}, y={self.y}, z={self.z}) at {hex(id(self))}"

    def __str__(self) -> str:
        vec_str = f"Vec2(x={self.x}, y={self.y})"
        if self.z != 0.0:
            vec_str += f" at z={self.z}"
        return vec_str
    
    def __eq__(self, value: Self):
        if not isinstance(value, Vec2):
            return False
        return value.x == self.x and value.y == self.y

class Vec2Array(List[Vec2]):
    """ 
    Array of Vec2 objects stored as a single numpy array for efficiency. 
    If iterable of Vec2 is provided, constructs from that.
    This will take ownership of the data, so changes to the Vec2Array will affect the original data.
    """
    def __init__(self, vectors: Union[Iterable[Vec2], np.ndarray]):
        self._vectors: List[Vec2] = []
        if not isinstance(vectors, np.ndarray):
            v_list = []
            for vector in vectors:
                v_list.append(vector._data)
                self._vectors.append(vector)
            vectors = np.array(v_list, dtype=np.float32)
        if not vectors.ndim == 2 or vectors.shape[1] not in (2, 3):
            raise ValueError("Numpy array must be of shape (N, 2) or (N, 3)")
        if vectors.shape[1] == 2:
            self._data = np.hstack((vectors, np.zeros((vectors.shape[0], 1), dtype=np.float32)))
        else:
            self._data = vectors.astype(np.float32)
        # Update vector references so modifications to Vec2Array reflect in Vec2 objects
        for i in range(self._data.shape[0]):
            if i < len(self._vectors):
                self._vectors[i]._data = self._data[i]
            else:
                self._vectors.append(Vec2(data=self._data[i]))

    def __len__(self) -> int:
        return self._data.shape[0]

    def __getitem__(self, index: int) -> Vec2:
        return self._vectors[index]

    def __iter__(self) -> Iterator[Vec2]:
        for vec in self._vectors:
            yield vec

    def translate(self, vector: Vec2):
        """ Translates all vectors by another vector. """
        self._data += vector._data

    def translated(self, vector: Vec2) -> Self:
        """ Returns a new Vec2Array that is the translation of this array by another vector. """
        new_data = self._data + vector._data
        return self.from_array(new_data)
  
    def rotate(self, direction: Vec2):
        """ Rotates all vectors by another vector (direction). """
        dx, dy = direction.normalised()

        x = self._data[:, 0]
        y = self._data[:, 1]

        self._data[:, 0] = y * dx + x * dy
        self._data[:, 1] = -x * dx + y * dy

    def rotated(self, direction: Vec2) -> Self:
        """ Returns a new Vec2Array that is the rotation of this array by another vector (direction). """
        dx, dy = direction.normalised()

        x = self._data[:, 0]
        y = self._data[:, 1]

        new_x = y * dx + x * dy
        new_y = -x * dx + y * dy

        new_arr = self._data.copy()
        new_arr[:, 0] = new_x
        new_arr[:, 1] = new_y
        return self.from_array(new_arr)
    
    @classmethod
    def from_array(cls, array: np.ndarray) -> Self:
        """ Creates a Vec2Array from a numpy array of shape (N, 2) or (N, 3). """
        obj = cls.__new__(cls)
        Vec2Array.__init__(obj, array)
        return obj

    def __mul__(self, value: float) -> Self:
        new_data = self._data[:, 0:2] * value
        new_arr = self._data.copy()
        new_arr[:, 0:2] = new_data
        return self.from_array(new_arr)