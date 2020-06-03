from popurri_tokens import *
from error_tokens import *
from copy import deepcopy
import math


class MemoryHandler():
    '''
    This class is used to simulate a memory with virtual addresses,
    it hosts four contexts (GLOBAL, LOCAL, TEMPORAL, CONSTANT), which
    all allocate 2000 spaces (by default) for each data type (INT, FLOAT, BOOL, STRING, POINTER).
    '''
    snapshot = None
    context_offset = None
    type_offset = None

    def __init__(self, context_offset=10000):
        '''
        Creates 4 memory contexts (GLOBAL, LOCAL, TEMPORAL, CONSTANT) with default size of 10k
        0     ->  9999 : GLOBAL
        10000 -> 19999 : LOCAL
        20000 -> 29999 : TEMPORAL
        30000 -> 39999 : CONSTANT
        '''
        self.context_offset = context_offset
        self.type_offset = int(context_offset / 5)

        if self.type_offset % 1 != 0:
            raise Exception('ERROR: \'context_offset\' must be divisible by 4')

        self.contexts = {}
        for i, ctx in enumerate([GLOBAL, LOCAL, TEMPORAL, CONSTANT]):
            self.contexts[ctx] = MemoryContext(
                start=context_offset * i, max_size=self.type_offset)

    def reserve(self, context, dtype, value=None):
        'reserves an address; assigns value if given'
        ctxMemory = self.contexts[context]
        reserved_address = ctxMemory.reserveAddress(dtype)

        if value is not None:
            ctxMemory.updateAddress(
                address=reserved_address,
                dtype=dtype,
                value=value
            )

        dtype -= INT
        return ctxMemory.start + reserved_address + (self.type_offset * dtype)

    def update(self, address, value):
        'Updates the given virtual address with the specified value'

        address, context = self.getContextAddress(address)
        dtype = self.getAddressType(address)

        if tokenizeByValue(value) != dtype and dtype is not POINTER:
            msg = EXPECTED_TYPE.format(stringifyToken(
                dtype), stringifyToken(tokenizeByValue(value)))
            raise Exception(f'ERROR: {msg}')

        # obtains the relative address within context address stack [1 -> TYPE_OFFSET]
        address -= ((dtype - INT) * self.type_offset)

        # Update value
        self.contexts[context].updateAddress(address, dtype, value)

    def getContextAddress(self, address):
        '''
        Returns address without context offset (i.e. 0 -> 9999)
        and its respective context (GLOBAL, LOCAL, TEMPORAL or CONSTANT).
        '''

        for i, ctx in enumerate([GLOBAL, LOCAL, TEMPORAL, CONSTANT]):
            start = self.context_offset * i
            end = self.context_offset * (i + 1) - 1
            if address in range(start, end):
                return (address - start, ctx)

        return (None, None)

    def getAddressType(self, address):
        'obtains the data type from address [INT, FLOAT, BOOL, STRING, POINTER]'
        return math.floor(address / self.type_offset % 5) + INT

    def getValue(self, address):
        'Obtains the value stored in the given virtual address'
        address, context = self.getContextAddress(address)
        dtype = self.getAddressType(address)
        address -= ((dtype - INT) * self.type_offset)

        return self.contexts[context].getValue(address, dtype)

    def saveSnapshot(self, context=LOCAL):
        'Saves a copy of all the memory sections in the given context'
        self.snapshot = deepcopy(self.contexts[context])

    def restoreSnapshot(self, context=LOCAL):
        'Restores a (previously saved) copy of the memory sections into the given context'
        self.contexts[context] = deepcopy(self.snapshot)

    def flush(self, context=LOCAL):
        'Deletes all memory for the specified context'
        start_offset = context - GLOBAL
        self.contexts[context] = MemoryContext(
            start=self.context_offset * start_offset, max_size=self.type_offset)

    def count(self, context=LOCAL):
        'Returns a tuple with the amount of items allocated in each memory section'
        memCtx = self.contexts[context].sections
        return tuple([len(v) for v in memCtx.values()])


class MemoryContext():
    '''
    This class is intended to be used by MemoryHandler, it's used to allocate.
    the 5 default data types in Popurri
    '''
    default_val_map = {
        INT: 0,
        FLOAT: 0.0,
        BOOL: False,
        STRING: '',
        POINTER: None
    }

    def __init__(self, start, max_size):
        '''
        Initiates the empty MemoryContext object, it accepts two parameters:
            - start: starting memory address for this Memory context
            - max_size: limit of elements a given type section can allocate
        '''
        self.start = start
        self.sections = {
            INT: [],
            FLOAT: [],
            BOOL: [],
            STRING: [],
            POINTER: []
        }
        self.allocations = { k:0 for k,v in self.sections.items() }
        self.max_size = max_size

    def reserveAddress(self, dtype):
        '''
        Increase the list size of the given type (INT, FLOAT, BOOL, STRING).
        returns the local address of the reserved space
        '''
        if self.allocations[dtype] == self.max_size:
            raise Exception(
                f'ERROR: Cannot allocate any more values of type "{stringifyToken(dtype)}", limit is {self.max_size}')

        self.sections[dtype].append(self.default_val_map[dtype])
        self.allocations[dtype] += 1
        return len(self.sections[dtype]) - 1

    def updateAddress(self, address, dtype, value=None):
        'Updates the localized address (i.e. without context offset) with the specified value.'
        if value is None:
            return

        self.sections[dtype][address] = value

    def getValue(self, address, dtype):
        'Returns the value stored in the localized address'
        return self.sections[dtype][address]
