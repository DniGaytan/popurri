from popurri_tokens import *

# Supported Operators
'''
boolOp    : 'and' | 'or'
cmpOp     : '<' | '<=' | '>' | '>=' | 'is' | 'is' 'not'
addOp     : '+' | '-'
multDivOp : '*' | '/' | '%'
assignOp  : '=' | '+=' | '-=' | '*=' | '/=' | '%='
expOp     : '**'
'''

# Supported Types
'''
TYPE      :  'int' | 'float' | 'string' | 'bool' | '[float]' | '[int]' | '[bool]'
'''


def bailaMijaConElSeñor(baile, mija=None, sr=None):
    '''
    Esta funcion checa si mija (l_type) baila (op) con el señor (r_type).
    Es decir, verifica si es posible ejecutar la dada operación entre los tipos proporcionados
    '''
    return bailes[baile].get((mija, sr), None)

# Operations between user-defined classes are NOT allowed


# This semantic cube should be accesed using .get(), since it only describxes valid operations
# So the get() function handles an unvalid combination of types
bailes = {
    #### boolOp ####
    ANDOP: {
        (BOOL, BOOL): BOOL
    },
    OROP: {
        (BOOL, BOOL): BOOL
    },
    #### cmpOp ####
    LESSER: {
        (INT, INT): BOOL,
        (INT, FLOAT): BOOL,
        (FLOAT, INT): BOOL,
        (FLOAT, FLOAT): BOOL
    },
    LESSEREQ: {
        (INT, INT): BOOL,
        (INT, FLOAT): BOOL,
        (FLOAT, INT): BOOL,
        (FLOAT, FLOAT): BOOL
    },
    GREATER: {
        (INT, INT): BOOL,
        (INT, FLOAT): BOOL,
        (FLOAT, INT): BOOL,
        (FLOAT, FLOAT): BOOL
    },
    GREATEREQ: {
        (INT, INT): BOOL,
        (INT, FLOAT): BOOL,
        (FLOAT, INT): BOOL,
        (FLOAT, FLOAT): BOOL
    },
    EQUAL: {
        # Any
    },
    NOTEQUAL: {
        # Any
    },
    #### addOp ####
    ADD: {
        (INT, INT): INT,
        (INT, FLOAT): FLOAT,
        (FLOAT, INT): FLOAT,
        (FLOAT, FLOAT): FLOAT,
        # "a" + "bc" = "abc"
        (STRING, STRING): STRING,
        # +10
        (NONE, INT): INT,
        # +3.14
        (NONE, FLOAT): FLOAT
    },
    MINUS: {
        (INT, INT): INT,
        (INT, FLOAT): FLOAT,
        (FLOAT, INT): FLOAT,
        (FLOAT, FLOAT): FLOAT,
    },
    #### multDivOp ####
    MULT: {
        (INT, INT): INT,
        (INT, FLOAT): FLOAT,
        (FLOAT, INT): FLOAT,
        (FLOAT, FLOAT): FLOAT,
        # "a" * 3 = "aaa"
        (STRING, INT): STRING,
        (INT, STRING): STRING
    },
    DIV: {
        # 3 / 10 = 0.33333
        (INT, INT): FLOAT,
        (INT, FLOAT): FLOAT,
        (FLOAT, INT): FLOAT,
        (FLOAT, FLOAT): FLOAT
    },
    MOD: {
        (INT, INT): INT,
        (INT, FLOAT): FLOAT,
        (FLOAT, INT): FLOAT,
        (FLOAT, FLOAT): FLOAT
    },
    #### assignOp ####
    ASSIGN: {
        (INT, INT): INT,
        (INT, FLOAT): FLOAT,
        (FLOAT, INT): FLOAT,
        (FLOAT, FLOAT): FLOAT
    },
    #### expOp ####
    POWER: {
        (INT, INT): INT,
        (INT, FLOAT): FLOAT,
        (FLOAT, INT): FLOAT,
        (FLOAT, FLOAT): FLOAT
    },
    #### unaryAddOp ####
    UNARYADD: {
        # +10
        (NONE, INT): INT,
        # +3.14
        (NONE, FLOAT): FLOAT
    },
    UNARYMINUS: {
        # -10
        (NONE, INT): INT,
        # -3.14
        (NONE, FLOAT): FLOAT
    }
}

# Append all combinations to "is" and "is not" operators
types = [INT, FLOAT, STRING, BOOL]
for op in [EQUAL, NOTEQUAL]:
    for left in types:
        for right in types:
            bailes[op][(left, right)] = BOOL


# TYPE      :  'int' | 'float' | 'string' | 'bool' | '[float]' | '[int]' | '[bool]'
