from antlr4 import *
from antlr_parser.PopurriParser import PopurriParser
from popurri_tokens import *
from error_tokens import *
from semantic_cube import bailaMijaConElSeñor
from memory import MemoryHandler
from copy import deepcopy
import jsbeautifier as js
import json


def pprint(*args):
    'Helper to pretty print any object with JSON style'
    opts = js.default_options()
    opts.indent_size = 2
    for arg in args:
        print(js.beautify(json.dumps(arg, default=vars), opts))


def error(ctx, msg):
    'Creates exception object, with the given message and line'
    return Exception(f'ERROR ON LINE {ctx.start.line}: {msg}')


class QuadWrapper():
    '''
    Handles all quadruple generation related stuff
    '''

    def __init__(self):
        self.quads = []
        self.quads_ptr = 0
        self.type_stack = []
        self.operator_stack = []
        self.address_stack = []
        self.jump_stack = []
        self.break_stack = []
        self.dim_stack = []

    def insertQuad(self, quad, at=None):
        '''
        inserta un cuadruplo pasado por parametro a la lista de quads
        si [at] esta presente se inserta este cuadruplo en la posicion dada
        '''
        self.quads_ptr += 1
        if at is not None:
            self.quads.insert(at, quad.__str__())
        else:
            self.quads.append(quad.__str__())

    def fillQuadWith(self, filler, at):
        '''
        llena la ultima posicion [3] del cuadruplo encontrado utlizando el argumento [at]
        Esta funcion solo funciona para la familia GOTOs
        '''
        new_quad = list(self.quads[at])
        new_quad[3] = filler
        self.quads[at] = tuple(new_quad)

    def topOperator(self):
        'regresa el valor que se encuentra en el tope de la pila de operadores'
        if len(self.operator_stack) == 0 or self.operator_stack[-1] == FALSEBOTTOM:
            return None

        return self.operator_stack[-1]

    def topJump(self):
        'regresa el valor que se encuentra en el tope de la pila de saltos'
        return self.jump_stack[-1] if len(self.jump_stack) > 0 else None

    def topAddress(self):
        'regresa el valor que se encuentra en el tope de la pila de direcciones'
        return self.address_stack[-1] if len(self.address_stack) > 0 else None

    def popOperator(self):
        '''
        saca el valor que se encuentra en el tope de la pila de operadores
        '''
        if len(self.operator_stack) == 0 or self.topOperator() == FALSEBOTTOM:
            return None

        return self.operator_stack.pop()

    def popAddress(self):
        '''
        saca el valor que se encuentra en el tope de la pila de address
        '''
        return self.address_stack.pop() if len(self.address_stack) > 0 else None

    def popJump(self):
        '''
        saca el valor que se encuentra en el tope de la pila de saltos
        '''
        return self.jump_stack.pop() if len(self.jump_stack) > 0 else None

    def popType(self):
        '''
        saca el valor que se encuentra en el tope de la pila de tipos
        '''
        return self.type_stack.pop() if len(self.type_stack) > 0 else None

    def popDim(self):
        '''
        saca el valor que se encuentra en el tope de la pila de dimensiones
        '''
        return self.dim_stack.pop() if len(self.dim_stack) > 0 else None

    # Flushes jumps until either stack is empty or it encounters a false-bottom

    def flushJumps(self):
        '''
        limpia todo la pia de saltos hasta encontrarse con un vacio
        o un fondo falso.
        '''
        jumps = []
        while True:
            j = self.popJump()
            if j is None or j is FALSEBOTTOM:
                break
            jumps.insert(0, j)
        return jumps

    def insertType(self, type):
        self.type_stack.append(tokenize(type))

    def insertAddress(self, address):
        '''
        Inserta una nueva direccion en la pila de direcciones
        '''
        self.address_stack.append(address)

    def insertDim(self, dim):
        '''
        Inserta una nueva direccion en la pila de dimensiones.
        '''
        self.dim_stack.append(dim)

    def insertOperator(self, operator):
        '''
        Inserta un nuevo operador en la pila de operadores
        '''
        self.operator_stack.append(tokenize(operator))

    def insertJump(self, jump=None):
        '''
        Inserta un nuevo salto en la pila de saltos
        '''
        self.jump_stack.append(self.quads_ptr if jump is None else jump)

    def validateTypes(self, ctx):
        '''
        ejecuta el cubo semantico para la validacion de los tipos de una operacion
        '''
        op = self.topOperator()
        r_type = self.popType()
        l_type = self.popType()
        res_type = bailaMijaConElSeñor(op, l_type, r_type)
        if res_type is None:
            raise error(ctx, TYPE_MISMATCH.format(
                        stringifyToken(op),
                        stringifyToken(l_type),
                        stringifyToken(r_type)
                        ))
        # Push resulting type into stack
        self.insertType(res_type)

        return res_type

    def generateQuad(self, ctx, memHandler):
        '''
        Se le pasa el [ctx] de una regla y [memHandler] como instancia de MemHandler
        para poder generar un cuadruplo utilizando los pops de las siguientes pilas
        [operator, address [2 veces]]
        y anade el resultado [tmp] a la pila de direcciones

        Es la forma de generar un cuadruplo que es consecuencia de alguna operacion
        '''
        tmp_type = self.validateTypes(ctx)

        tmp = memHandler.reserve(
            context=TEMPORAL,
            dtype=tmp_type
        )

        self.insertQuad(Quadruple(
            op=self.popOperator(),
            r=self.popAddress(),
            l=self.popAddress(),
            res=tmp
        ))
        self.insertAddress(tmp)


class Quadruple():
    '''
    Esta clase lidia con la creacion de un cuadruplo y su obtencion
    '''

    def __init__(self, op, l=None, r=None, res=None):
        self.op = op
        # Arguments (In some cases one of both of them would be -1 indicating there is no value)
        self.l = l
        self.r = r
        # Where result of op(l, r) is stored
        # This is an address rather than a value
        self.res = res

    def __str__(self):
        '''
        obtencion del cuadruplo
        '''
        return (self.op, self.l, self.r, self.res)


class ContextWrapper():
    '''
    Esta es una tabla de procedimientos y stack de contextos
    Antes GlobalContext
    '''

    def __init__(self, variables=None, functions=None):
        self.variables = variables if variables else {}
        self.functions = functions if functions else {}
        self.context_stack = ['global']
        self.loop_stack = []

    def pushLoop(self, loop=True):
        return self.loop_stack.append(loop)

    def popLoop(self):
        '''
        saca el valor que se encuentra en el tope de la pila de ciclos
        '''
        return self.loop_stack.pop()

    def insideLoop(self):
        '''
        regresa [True] si la lista tiene algun elemento
        y [False] si la lista esta vacia
        '''
        return len(self.loop_stack) > 0

    def insideClass(self):
        '''
        regresa [True] si la lista tiene menos de dos elementos
        y [False] si la lista tiene mas de 2 elementos
        '''
        if len(self.context_stack) < 2:
            return False

        return 'class ' in self.top() or 'class ' in self.context_stack[-2]

    def top(self):
        '''
        regresa el valor que se encuentra en el tope de [context_stack]
        '''
        return self.context_stack[-1]

    def pop(self):
        '''
        saca el valor que se encuentra en el tope de [context_stack]
        '''
        return self.context_stack.pop()

    def push(self, ctx):
        '''
        inserta una copia del [ctx] pasado por parametro al context_stack
        '''
        return self.context_stack.append(deepcopy(ctx))

    def getVariableByAddress(self, address):
        '''
        searches within the whole variables values range
        for the address match to the address passed as parameter
        if a match exists, returns the var object
        otherwise exits loop and return None
        '''
        for ctx in self.variables.values():  # Iterate over contexts
            for var in ctx.values():
                if type(var) == dict:  # Inside function varTable
                    for var in var.values():
                        if type(var) == dict:  # Var is object, iterate over attributes
                            for attr in var.values():
                                if address == attr.address:
                                    return attr
                        elif address == var.address:
                            return var
                elif address == var.address:
                    return var
        return None

    def getVariable(self, var_id, context="global", insideClass=False):
        '''
        returns the variable object using [var_id]
        The algorithm searches within the context passed as argument
        and in case of insideClass being true, the algorithm will filter all the variables
        that live within the class context
        '''
        variables = self.variables[self.getClassContext(
        )] if insideClass else self.variables
        if context not in variables:
            return None

        return variables[context].get(str(var_id), None)

    def getFunction(self, func_id, context="global"):
        '''
        returns the function object within functions table by using the func_id and context
        if it fails in the searcch, None is returned
        '''
        func_id = str(func_id)
        if 'func ' not in func_id:
            func_id = 'func ' + func_id

        if context in self.functions:
            return self.functions[context].get(str(func_id), None)
        else:
            return None

    def getCurrentFunction(self):
        '''
        returns the function object within functions using the context_stack top value
        '''
        func_id = self.pop()
        func_ctx_id = self.top() if self.top() != func_id else 'global'
        self.push(func_id)  # Re-push current context
        return self.getFunction(func_id, context=func_ctx_id)

    def getClassContext(self):
        '''
        returns the top class object from context_stack
        '''
        if len(self.context_stack) < 2:
            return None

        if 'class ' in self.top():
            return self.top()
        elif 'class ' in self.context_stack[-2]:
            return self.context_stack[-2]

        return None

    def getAttributes(self, class_id):
        '''
        returns all attributes from a class using class_id
        '''
        if 'class ' not in class_id:
            class_id = 'class ' + class_id

        if class_id not in self.variables:
            return None

        return {k: deepcopy(v) for k, v in self.variables[class_id].items() if type(v) != dict}

    def addVariable(self, var, context="global", insideClass=False):
        'Adds the variable object to the corresponding context'
        variables = self.variables[self.getClassContext()] if insideClass else self.variables

        if context in variables:
            variables[context][var.id] = var
        else:
            variables[context] = {
                var.id: var
            }

    def addFunction(self, func, context="global"):
        '''
        inserts a new function into the funcs table and in the right context
        '''
        func_id = 'func ' + func.id
        if context in self.functions:
            self.functions[context][func_id] = func
        else:
            self.functions[context] = {
                func_id: func
            }

    def getVariableIfExists(self, var_id):
        '''
        search for a variable with var_id, if it exists returns the var and its ctx
        otherwise, return None and None
        '''
        if self.insideClass():
            class_name = self.getClassContext()
            if self.top() not in self.variables[class_name]:
                return None

            return self.variables[class_name][self.top()].get(str(var_id), None), self.top()

        for ctx in self.context_stack[::-1]:
            if ctx not in self.variables:
                continue

            var = self.variables[ctx].get(str(var_id), None)
            if var is not None:
                return var, ctx

        return None, None

    def getFunctionIfExists(self, func_id):
        '''
        search for a function with var_id, if it exists returns the var and its ctx
        otherwise, return None and None
        '''
        func_id = str(func_id)
        if 'func ' not in func_id:
            func_id = 'func ' + func_id

        for ctx in self.context_stack[::-1]:
            if ctx not in self.functions:
                continue

            var = self.functions[ctx].get(str(func_id), None)
            if var is not None:
                return var

        return None

    def varExistsInContext(self, var_id, ctx='global'):
        '''
        search for a var with [var_id] in the specified context
        if it exists, return the True, otherwise return False
        '''
        if ctx not in self.variables:
            return False

        return self.variables[ctx].get(str(var_id), None) is not None

    def functionExistsInContext(self, func_id, ctx='global'):
        '''
        search for a func with [func_id] in the specified context
        if it exists, return the True, otherwise return False
        '''
        func_id = str(func_id)
        if 'func ' not in func_id:
            func_id = 'func ' + func_id

        if ctx not in self.functions:
            return False

        return self.functions[ctx].get(str(func_id), None) is not None

    def classExists(self, id):
        '''
        search for a class with [id]
        if it exists, return the True, otherwise return False
        '''
        id = str(id)
        if 'class ' not in id:
            id = 'class ' + id

        return id in self.variables or id in self.functions


class Variable():
    '''
    Esto nos permite simular la creacion de variables. Inicializandolas con atributos predeterminados.
    [id] es el identificador con el que se podra localizar la actual variable. Ej. var edad : int. Donde edad es el ID.
    [type] es el tipo de dato con el que la variable estara relacionada. Ej. var edad : int. Donde int es el tipo de dato.
    [value] es el valor inicial que tendra la variable. Ej. var edad = 25. Donde 25 es el valor inicial.
    '''

    def __init__(self, id, access_type=PUBLIC, type=NONE, address=None, paramNo=None, arraySize=None):
        self.access_type = access_type
        self.id = str(id)
        self.type = tokenize(type)
        self.address = address
        self.paramNo = paramNo
        self.arraySize = arraySize

    def isArray(self):
        return self.arraySize != None


class Function():
    '''
    Esto nos permite simular la creacion de funciones. Inicializandolas con atributos predeterminados.
    [id] es el identificador con el que se podra localizar la funcion actual. Ej. func habla() {}. Donde habla es el identificador.
    [return_type] es el tipo de dato que regresara la funcion al terminar su ejecucion. Void es el tipo predeterminado.
    '''

    def __init__(self, id, return_type=NONE, access_type=PUBLIC, quads_range=(-1, -1), paramTypes=None, era_local=(), era_tmp=()):
        self.id = str(id)
        self.return_type = tokenize(return_type)
        self.access_type = access_type
        self.quads_range = quads_range
        self.paramTypes = paramTypes if paramTypes else []
        self.era_local = era_local
        self.era_tmp = era_tmp

    def updateQuadsRange(self, start=None, end=None):
        '''
        Updates the current function quadsRange
        '''
        quads_range = list(self.quads_range)
        if start is not None:
            quads_range[0] = start
        if end is not None:
            quads_range[1] = end
        self.quads_range = tuple(quads_range)

    def addParamType(self, ty):
        '''
        appends a new paramType if requested
        '''
        self.paramTypes.append(ty)


class PopurriListener(ParseTreeListener):
    '''
    -Esta clase nos permite simular la creacion de tabla de variables
    -Cada funcion 'enter' representa el estado cuando se inicia una regla
    -Cada funcion 'exit' representa el estado cuando se acaba una regla
    '''

    def __init__(self, mem_size, debug_info=False):
        self.ctxWrapper = ContextWrapper()
        self.quadWrapper = QuadWrapper()
        self.memHandler = MemoryHandler(mem_size)
        # Flags for internal compiler use
        self.if_cond = False
        self.inside_expression = False
        self.param_count = -1
        self.func_count = -1
        self.func_returned_val = False
        self.debug_info = debug_info

    def enterProgram(self, ctx):
        '''
        [Program] marca el inicio de las reglas de la gramatica. Aqui inicia la fase de compilacion.
        '''
        goto_quad = Quadruple(GOTO)
        self.quadWrapper.insertQuad(goto_quad)
        self.quadWrapper.insertJump()
        self.func_count = len(ctx.function())
        for klass in ctx.classDeclaration():
            self.func_count += len(klass.method())
        pass

    def printDebug(self):
        'Pretty print all debug information needed for developers.'
        print("--VARIABLES--")
        pprint(self.ctxWrapper.variables)
        print("--FUNCTIONS--")
        pprint(self.ctxWrapper.functions)

        print('quads_stack = [')
        for i, x in enumerate(self.quadWrapper.quads, start=1):
            tmp = list(x)
            tmp[0] = stringifyToken(x[0])
            print('\t', i, tuple(tmp))
        print(']')

        print('address_stack = ', end='')
        pprint(self.quadWrapper.address_stack)
        print('operator_stack = ', end='')
        pprint(self.quadWrapper.operator_stack)
        print('type_stack = ', end='')
        pprint(self.quadWrapper.type_stack)
        print('jump_stack = ', end='')
        pprint(self.quadWrapper.jump_stack)
        print('quad_ptr = ', end='')
        pprint(self.quadWrapper.quads_ptr)

        for ctx in [GLOBAL, LOCAL, CONSTANT, TEMPORAL]:
            context = self.memHandler.contexts[ctx].sections
            print(stringifyToken(ctx), '= {')
            for section in context:
                print('    ', stringifyToken(section), context[section])
            print('}')

    def exitProgram(self, ctx):
        '''
        [Program] marca el final de las reglas de la gramatica. Aqui termina la fase de compilacion.
        '''
        if self.debug_info:
            self.printDebug()

    def enterModule(self, ctx):
        '''
        [Module] no afecta ningun aspecto del compilador o lenguaje, por lo que se ignora
        '''
        pass

    def exitModule(self, ctx):
        '''
        [Module] no afecta ningun aspecto del compilador o lenguaje, por lo que se ignora
        '''
        pass

    def enterDeclarations(self, ctx):
        '''
        [Declarations] is the first part of the rule Declarations
        This rule fills the GOTO generated from program (So class quads dont get executed)
        '''
        if self.ctxWrapper.top() == 'global':
            # Fill GOTO to declarations start (so classes dont get executed)
            self.quadWrapper.fillQuadWith(
                self.quadWrapper.quads_ptr + 1,
                at=self.quadWrapper.popJump() - 1
            )

    def exitDeclarations(self, ctx):
        '''
        [Declarations] is the second part of the rule Declarations
        This rule generates a new GOTO quad (which will be filled when "main" starts)
        '''
        if self.ctxWrapper.top() == 'global':
            goto_quad = Quadruple(GOTO)
            self.quadWrapper.insertQuad(goto_quad)
            self.quadWrapper.insertJump()

    def enterDeclaration(self, ctx):
        '''
        [Declaration] is the first part of the rule Declaration
        all variable declaration in the global context is handled in this function
        the function checks every aspect of the variable to create and assign the corresponding
        memory slot and insert a new vars table entry
        '''
        # Checks if global is already declared
        if self.ctxWrapper.varExistsInContext(ctx.ID(0), ctx=self.ctxWrapper.top()):
            raise error(ctx, VAR_REDEFINITION.format(str(ctx.ID(0))))

        var = None
        # var has data_type : INT, FLOAT, STRING, BOOL
        if ctx.TYPE() is not None:
            dtype = tokenize(ctx.TYPE())

            reserved_address = self.memHandler.reserve(
                context=tokenizeContext(self.ctxWrapper.top()),
                dtype=dtype
            )

            var = Variable(
                id=ctx.ID(0),
                type=ctx.TYPE(),
                address=reserved_address
            )

            # var is an array
            if ctx.CONST_I() is not None:
                mem_reservations = int(str(ctx.CONST_I())) - 1
                var.arraySize = mem_reservations + 1

                for _ in range(mem_reservations - 1):
                    reserved_address = self.memHandler.reserve(
                        context=tokenizeContext(self.ctxWrapper.top()),
                        dtype=dtype
                    )

        # var is type object
        elif len(ctx.ID()) == 2:
            if ctx.assignment() is not None:
                raise error(ctx, CLASS_ASSIGNMENT)

            class_name = str(ctx.ID(1))
            if not self.ctxWrapper.classExists(class_name):
                raise error(ctx, UNDEF_CLASS.format(class_name))

            # Re-allocate attributes in current context
            attrs = self.ctxWrapper.getAttributes(class_name)
            for attr in attrs.values():
                attr.address = self.memHandler.reserve(
                    context=tokenizeContext(self.ctxWrapper.top()),
                    dtype=attr.type
                )
                if attr.isArray():  # Allocate slots
                    for _ in range(attr.arraySize):
                        self.memHandler.reserve(
                            context=tokenizeContext(self.ctxWrapper.top()),
                            dtype=attr.type
                        )

            context_vars = self.ctxWrapper.variables
            if self.ctxWrapper.insideClass():
                context_vars = context_vars[self.ctxWrapper.getClassContext()]

            # Add self var (so we know what type is this object)
            var_id = str(ctx.ID(0))
            self_var = Variable(id='self')
            self_var.type = class_name
            attrs[self_var.id] = self_var

            curr_ctx = self.ctxWrapper.top()
            if curr_ctx not in context_vars:
                context_vars[curr_ctx] = {var_id: attrs}
            else:
                context_vars[curr_ctx][var_id] = attrs

            return

        # Var type will be declared implicitly via assignment
        elif ctx.assignment() is not None:
            var = Variable(id=ctx.ID(0))
        else:
            raise error(ctx, MUST_DECLARE_VAR_TYPE.format(str(ctx.ID(0))))

        if ctx.assignment() is not None:
            if var.address is not None:
                self.quadWrapper.insertAddress(var.address)
            else:
                self.quadWrapper.insertAddress(var.id)
            self.quadWrapper.insertType(var.type)

        self.ctxWrapper.addVariable(
            var,
            context=self.ctxWrapper.top(),
            insideClass=self.ctxWrapper.insideClass()
        )

    def exitDeclaration(self, ctx):
        pass

    def createFunction(self, ctx):
        '''
        This is the automated mechanism for the function object creation.
        By passing the context from the rule, this function can generate the
        function object to insert and returns it to the caller.
        '''
        func = Function(
            id=ctx.ID()
        )
        # Function has params
        if ctx.funcParams() is not None:
            no_params = len(ctx.funcParams().ID())
            for i in range(no_params):
                ty = tokenize(ctx.funcParams().TYPE(i))
                func.addParamType(ty)

        # Function isnt void
        if ctx.TYPE() is not None:
            func.return_type = tokenize(ctx.TYPE())

        func.updateQuadsRange(start=self.quadWrapper.quads_ptr + 1)

        return func

    def enterFunction(self, ctx):
        '''
        [Function] first part of the rule Function
        Creates the Function object and adds it to the global funcTable.
        It also pushes the function id to the context stack
        '''
        if self.ctxWrapper.functionExistsInContext(ctx.ID(), 'global'):
            raise error(ctx, FUNC_REDEFINITION.format(str(ctx.ID())))

        func = self.createFunction(ctx)
        self.ctxWrapper.addFunction(func)
        self.ctxWrapper.push('func ' + func.id)

    def exitFunction(self, ctx):
        '''
        [Function] is the second part of the rule Function
        after all the internal function process ends, this function
        will update current function details as: saving memory, and updating
        quad range
        '''
        func = self.ctxWrapper.getFunction(self.ctxWrapper.top())
        # If function is non-void verify it had at least one return inside
        if func.return_type != NONE and not self.func_returned_val:
            raise error(ctx, MUST_RETURN_ON_NON_VOID_FUNC.format(func.id))

        if func.quads_range[0] > self.quadWrapper.quads_ptr:
            func.updateQuadsRange(start=-1)
        else:
            func.updateQuadsRange(end=self.quadWrapper.quads_ptr)
            self.quadWrapper.insertQuad(Quadruple(
                op=ENDPROC
            ))

        self.ctxWrapper.pop()
        self.func_count -= 1
        self.func_returned_val = False  # Reset flag

        # Save req memory and then flush it
        func.era_local = self.memHandler.count(LOCAL)
        func.era_tmp = self.memHandler.count(TEMPORAL)
        self.memHandler.flush(LOCAL)
        self.memHandler.flush(TEMPORAL)
        pass

    def getAccessType(self, ctx):
        '''
        Tokenizes the access type of the context, returns PUBLIC token
        if not present.
        '''
        ty = ctx.ACCESS_TYPE()
        return PUBLIC if ty is None else tokenize(ty)

    def enterClassDeclaration(self, ctx):
        '''
        [ClassDeclaration] is the first part of the rule ClassDeclaration

        This function replaces declarations and attributes in order to simplify
        the process of handling data inside classes.

        This rule handles attribute and method inheritance, and also parses the class'
        attributes & methods and adds them to their respective tables.

        It also allocates the class attributes into the LOCAL memory and saves a snapshot
        of this context, so they don't get flushed when parsing methods.
        '''
        class_id = str(ctx.ID())
        if self.ctxWrapper.classExists(class_id):
            raise error(ctx, CLASS_REDEFINITION.format(class_id))

        class_id = 'class ' + class_id
        self.ctxWrapper.push(class_id)

        parent_id = None
        if ctx.parent() is not None:
            parent_id = 'class ' + str(ctx.parent().ID())
            if not self.ctxWrapper.classExists(parent_id):
                raise error(ctx, UNDEF_PARENT.format(parent_id, class_id))

            # Inherit attributes
            for attr in self.ctxWrapper.variables[parent_id].values():
                if (type(attr) != dict  # check if it's a method varTable
                        and attr.access_type != PRIVATE):
                    self.ctxWrapper.addVariable(attr, class_id)
                    self.memHandler.reserve(
                        context=LOCAL,
                        dtype=attr.type
                    )

            # Inherit functions
            for func in self.ctxWrapper.functions[parent_id].values():
                if func.access_type != PRIVATE:
                    self.ctxWrapper.addFunction(func, class_id)
                    # Inherit varTable
                    method_vars = self.ctxWrapper.variables[parent_id].get('func ' + func.id, None)
                    if method_vars:
                        self.ctxWrapper.variables[class_id]['func ' + func.id] = method_vars # FIXME ??

        # Parse class attributes
        for declarations in ctx.attributes():
            access_type = self.getAccessType(declarations)

            for attr in declarations.attribute():
                # Raise error if re-declaration (ignore inherited methods)
                if (self.ctxWrapper.varExistsInContext(attr.ID(), class_id)
                        and not self.ctxWrapper.varExistsInContext(attr.ID(), parent_id)):
                    raise error(ctx, VAR_REDEFINITION.format(attr.ID()))

                reserved_address = self.memHandler.reserve(
                    context=tokenizeContext(self.ctxWrapper.top()),
                    dtype=tokenize(attr.TYPE())
                )

                var = Variable(
                    id=attr.ID(),
                    type=attr.TYPE(),
                    access_type=access_type,
                    address=reserved_address
                )

                # Attribute is an array, allocate space for its size
                if attr.CONST_I() is not None:
                    mem_reservations = int(str(attr.CONST_I())) - 1
                    var.arraySize = mem_reservations + 1

                    # First address is already reserved
                    for _ in range(mem_reservations - 1):
                        reserved_address = self.memHandler.reserve(
                            context=tokenizeContext(self.ctxWrapper.top()),
                            dtype=tokenize(attr.TYPE())
                        )

                self.ctxWrapper.addVariable(var, class_id)

        if class_id not in self.ctxWrapper.variables:  # Add empty varTable if no attributes
            self.ctxWrapper.variables[class_id] = {}

        # Parse class methods
        for method in ctx.method():
            access_type = self.getAccessType(method)
            # Raise error if re-declaration (ignore inherited methods)
            if (self.ctxWrapper.functionExistsInContext(method.ID(), class_id)
                    and not self.ctxWrapper.functionExistsInContext(method.ID(), parent_id)):
                raise error(ctx, FUNC_REDEFINITION.format(str(method.ID())))

            method = self.createFunction(method)
            method.access_type = access_type

            self.ctxWrapper.addFunction(method, class_id)

        # Save snapshot of memory (so we can retain attributes after every method flush)
        self.memHandler.saveSnapshot(LOCAL)
        pass

    def exitClassDeclaration(self, ctx):
        '''
        [ClassDeclaration] is the second part of the rule ClassDeclaration

        this will pop the class context from the context stack
        and empties the LOCAL and TEMPORARY contexts from memory
        '''
        self.ctxWrapper.pop()
        self.memHandler.flush(LOCAL)
        pass

    def enterParent(self, ctx):
        pass

    def exitParent(self, ctx):
        pass

    def enterAttributes(self, ctx):
        pass

    def exitAttributes(self, ctx):
        pass

    def enterAttribute(self, ctx):
        pass

    def exitAttribute(self, ctx):
        pass

    def enterMethod(self, ctx):
        '''
        [Method] this is the first part of the rule Method
        this function updates the method's starting quad
        '''
        class_name = self.ctxWrapper.top()
        self.ctxWrapper.push('func ' + str(ctx.ID()))
        method = self.ctxWrapper.getFunction(
            self.ctxWrapper.top(), context=class_name)
        method.updateQuadsRange(start=self.quadWrapper.quads_ptr + 1)

    def exitMethod(self, ctx):
        '''
        [Method] this is the second part of the rule Method

        this function updates the method's ending quad (unless the function is empty)
        and the LOCAL and TEMPORARY memory required by the method (era_local & era_tmp)
        Also generates an ENDPROC quadruple
        '''
        name = self.ctxWrapper.pop()
        method = self.ctxWrapper.getFunction(
            name, context=self.ctxWrapper.top())
        if method.quads_range[0] > self.quadWrapper.quads_ptr:
            method.updateQuadsRange(start=-1)
        else:
            method.updateQuadsRange(end=self.quadWrapper.quads_ptr)

        self.quadWrapper.insertQuad(Quadruple(
            op=ENDPROC
        ))
        self.func_count -= 1
        # Save required memory for method & flush local & tmp memory
        method.era_local = self.memHandler.count(LOCAL)
        method.era_tmp = self.memHandler.count(TEMPORAL)
        self.memHandler.restoreSnapshot(LOCAL)
        self.memHandler.flush(TEMPORAL)

    def enterStatement(self, ctx):
        '''
        [Statement] this is the first part of the rule Statement

        If all functions have been parsed, then this statement is the "main" start,
        so the GOTO from global variable declaration is filled.
        '''
        self.inside_expression = False

        # Check if Main Start
        if self.func_count == 0:
            # Fill GOTO to main start (so funcs dont get executed)
            self.quadWrapper.fillQuadWith(
                self.quadWrapper.quads_ptr + 1,
                at=self.quadWrapper.popJump() - 1
            )
            self.func_count = -1  # Reset flag

        if ctx.indexation() is not None or ctx.assignment() is not None:
            self.validateCalledIds(ctx)

    def exitStatement(self, ctx):
        self.inside_expression = False  # Reset flag

    def enterBreakStmt(self, ctx):
        '''
        [BreakStmt] this is the first part of the rule BreakStmt

        A GOTO quadruple is generated and a jump is inserted for the compiler
        to know a break stmt needs to be processed later
        '''
        self.quadWrapper.insertJump()
        self.quadWrapper.insertQuad(Quadruple(GOTO))
        if not self.ctxWrapper.insideLoop():
            raise error(ctx, INVALID_BREAK_USE)

    def enterWhileLoop(self, ctx):
        '''
        [WhileLoop] this is the first part of the rule WhileLoop

        jump is inserted (Which will be used when filling the GOTOF quad)
        and a loop is pushed back into loop stack (used when verifying a break
        statement is being used correctly)
        '''
        self.if_cond = True  # Reuse flag to process condition
        self.quadWrapper.insertJump()
        self.ctxWrapper.pushLoop()

    def exitWhileLoop(self, ctx):
        '''
        [WhileLoop] this is the second part of the rule WhileLoop

        It generates a GOTO quad to loop start, fills any break GOTOs added with next quad
        And fills the GOTOF quad of the while cond
        '''
        # exit while GOTO quadruple is generated and the loop is popped from
        # the loop stack
        goto_quad = Quadruple(GOTO)
        self.quadWrapper.insertQuad(goto_quad)
        self.ctxWrapper.popLoop()

        # Fill any breaks that might've been added inside loop
        while True:
            brk = self.quadWrapper.popJump()
            if brk is None or brk == FALSEBOTTOM:
                break

            self.quadWrapper.fillQuadWith(
                self.quadWrapper.quads_ptr + 1,
                at=brk
            )

        # Fill while gotoF with next quad
        self.quadWrapper.fillQuadWith(
            self.quadWrapper.quads_ptr + 1,
            at=self.quadWrapper.popJump() - 1
        )

        # Fill loop-end goto with loop start
        self.quadWrapper.fillQuadWith(
            self.quadWrapper.popJump() + 1,
            at=self.quadWrapper.quads_ptr - 1
        )

    def enterIterable(self, ctx):
        'Parses iterable (i.e. array), and adds it to loop stack'
        if ctx.ID() is not None:
            self.validateCalledIds(ctx)
            iterable_addr = self.quadWrapper.topAddress()
            iterable = self.ctxWrapper.getVariableByAddress(iterable_addr)
            self.ctxWrapper.pushLoop(iterable)

    def enterForLoop(self, ctx):
        '''
        Creates the iterator variable and adds it to the current context varTable
        '''
        # Add iterator to global varTable
        iterator = Variable(
            id=str(ctx.ID()),
            type=stringifyToken(INT)
        )
        iterator.address = self.memHandler.reserve(
            context=TEMPORAL,
            dtype=INT
        )
        self.ctxWrapper.addVariable(
            iterator,
            context=self.ctxWrapper.top(),
            insideClass=self.ctxWrapper.insideClass()
        )
        self.ctxWrapper.pushLoop(iterator)

        # Gonna later fill GOTOV with loop start
        self.quadWrapper.insertJump()

    def exitForLoop(self, ctx):
        iterable = self.ctxWrapper.popLoop()
        iter = self.ctxWrapper.popLoop()

        # reserve memory for array index
        index_array = self.memHandler.reserve(
            context=TEMPORAL,
            dtype=INT,
            value=0
        )

        tmp = self.memHandler.reserve(
            context=TEMPORAL,
            dtype=BOOL
        )

        size_constant = self.memHandler.reserve(
            context=CONSTANT,
            dtype=INT,
            value=iterable.arraySize - 1)

        self.quadWrapper.insertQuad(
            Quadruple(
                op=LESSER,
                l=index_array,  # placeholder
                r=size_constant,  # placeholder
                res=tmp
            )
        )

        # [quad] GOTOF generation
        self.quadWrapper.insertJump()
        gotof_quad = Quadruple(GOTOF, l=tmp)
        self.quadWrapper.insertQuad(gotof_quad)

        # [quad] move iter to the next position in array

        iter_steps = self.memHandler.reserve(
            context=CONSTANT,
            dtype=INT,
            value=1)

        tmp = self.memHandler.reserve(
            context=TEMPORAL,
            dtype=INT)

        self.quadWrapper.insertQuad(
            Quadruple(
                op=ADD,
                l=iter_steps,  # placeholder
                r=index_array,
                res=tmp)
        )

        self.quadWrapper.insertQuad(
            Quadruple(
                op=ASSIGN,
                l=tmp,  # placeholder
                res=index_array)
        )

        tmp = self.memHandler.reserve(
            context=TEMPORAL,
            dtype=POINTER)

        iterable_address_constant = self.memHandler.reserve(
            context=CONSTANT,
            dtype=INT,
            value=iterable.address)

        self.quadWrapper.insertQuad(
            Quadruple(
                op=ADD,
                l=index_array,  # placeholder
                r=iterable_address_constant,  # placeholder
                res=tmp
            )
        )

        self.quadWrapper.insertQuad(
            Quadruple(
                op=ASSIGN,
                l=tmp,  # placeholder
                res=iter.address
            )
        )

        # [quad] GOTO generation
        goto_quad = Quadruple(GOTO)
        self.quadWrapper.insertQuad(goto_quad)

        # fill For loop GOTOF with next quad
        self.quadWrapper.fillQuadWith(
            self.quadWrapper.quads_ptr + 1,
            at=self.quadWrapper.popJump()
        )

        # fill For loop GOTO with forloop start
        self.quadWrapper.fillQuadWith(
            self.quadWrapper.popJump() + 1,
            at=self.quadWrapper.quads_ptr - 1
        )

    def enterBranch(self, ctx):
        self.quadWrapper.insertJump(FALSEBOTTOM)
        pass

    def exitBranch(self, ctx):
        '''
        [Branch] this is the second part of the rule Branch

        Fills all GOTOs generated by if, elseif and else end with
        the current quad_ptr
        '''
        self.if_cond = False

        # flush jumps inside else (to later be re-added)
        if ctx.elseStmt() is not None:
            else_jumps = self.quadWrapper.flushJumps()
        else:
            self.quadWrapper.flushJumps()  # Remove false bottom

        # Fill if and elseif GOTOs with next quad outside branch
        pending_jumps = []
        no_branches = 1 + len(ctx.elseIf())
        for _ in range(no_branches):
            pending_jumps += self.quadWrapper.flushJumps()

            branchEndJump = pending_jumps.pop()
            self.quadWrapper.fillQuadWith(
                self.quadWrapper.quads_ptr + 1,
                at=branchEndJump
            )

        self.quadWrapper.jump_stack += pending_jumps

        # Re-push else jumps
        if ctx.elseStmt() is not None:
            self.quadWrapper.jump_stack += else_jumps

    def enterIfStmt(self, ctx):
        '''
        [IfStmt] this is the first part of the rule IfStmt
        '''
        self.if_cond = True

    def exitIfStmt(self, ctx):
        '''
        Fills if GOTOF with next quad (i.e. elseif, else or new statement)
        while ignoring any breaks that might've been added inside if.
        '''
        # Other jumps (breaks) might've been pushed inside If
        pending_jumps = self.quadWrapper.flushJumps()

        # Fill GOTOF with next quad
        self.quadWrapper.fillQuadWith(
            self.quadWrapper.quads_ptr + 2,
            at=self.quadWrapper.popJump() - 1
        )

        # Re-push pending jumps
        self.quadWrapper.jump_stack += pending_jumps

        # creates GOTO quadruple
        goto_quad = Quadruple(GOTO)
        self.quadWrapper.insertJump()
        self.quadWrapper.insertJump(FALSEBOTTOM)
        self.quadWrapper.insertQuad(goto_quad)

    def enterElseIf(self, ctx):
        '''
        [ElseIf] this is the first part of the rule ElseIf
        '''
        self.if_cond = True

    def exitElseIf(self, ctx):
        '''
        [ElseIf] this is the first part of the rule ElseIf
        '''
        self.exitIfStmt(ctx)  # Rule is the same as if statement

    def enterElseStmt(self, ctx):
        pass

    def exitElseStmt(self, ctx):
        pass

    def enterReturnStmt(self, ctx):
        '''
        [ReturnStmt] this is the first part of the rule ReturnStmt.

        Verifies that return is being used inside non-void function.
        Sets flag so expression result is allocated
        '''
        if self.ctxWrapper.top() == 'global':
            raise error(ctx, RETURN_OUTSIDE_FUNC)

        # Return is inside function, verify if not void
        func = self.ctxWrapper.getCurrentFunction()
        if func.return_type == 'void':
            raise error(ctx, RETURN_ON_VOID_FUNC.format(func.id))

        self.inside_expression = True

    def exitReturnStmt(self, ctx):
        '''
        [ReturnStmt] this is the second part of the rule ReturnStmt

        Validates returning type matches function return type, generates
        GOTOR quad, and sets flag to specify that function did return value.
        '''

        # Validate return type matches function return type
        func = self.ctxWrapper.getCurrentFunction()
        return_type = self.quadWrapper.popType()
        if return_type != func.return_type:
            raise error(ctx, INVALID_RETURN_TYPE.format(
                stringifyToken(return_type),
                stringifyToken(func.return_type)
            ))

        self.quadWrapper.insertQuad(Quadruple(
            op=GOTOR,
            res=self.quadWrapper.popAddress()
        ))
        self.func_returned_val = True

    def exitCond(self, ctx):
        '''
        [Cond] this is the second part of the rule Cond

        If Cond is being used in a if, elseif or while, validate that the result
        is a boolean, and if so, generate a GOTOF.

        If Cond is being used inside a function call, generate PARAM quad
        '''
        if len(self.quadWrapper.operator_stack) > 0 and self.quadWrapper.operator_stack[-1] is FALSEBOTTOM:
            self.quadWrapper.popOperator()

        if self.if_cond:
            cond_ty = self.quadWrapper.popType()
            if cond_ty != BOOL:
                raise error(ctx, EXPECTED_BOOL.format(stringifyToken(cond_ty)))

            gotof_quad = Quadruple(
                GOTOF,
                l=self.quadWrapper.popAddress()
            )
            self.quadWrapper.insertQuad(gotof_quad)
            self.quadWrapper.insertJump()
            # False bottom for filling breaks inside if/loop
            self.quadWrapper.insertJump(FALSEBOTTOM)
            self.if_cond = False  # Reset flag

        # Function call
        if self.param_count != -1:
            self.quadWrapper.insertQuad(Quadruple(
                op=PARAM,
                l=self.quadWrapper.popAddress(),
                res='param ' + str(self.param_count)
            ))
            self.param_count += 1

    def exitCmp(self, ctx):
        if self.quadWrapper.topOperator() in [ANDOP, OROP]:
            self.quadWrapper.generateQuad(ctx, self.memHandler)

    def exitExp(self, ctx):
        if self.quadWrapper.topOperator() in [LESSER, LESSEREQ, GREATER, GREATEREQ, EQUAL, NOTEQUAL]:
            self.quadWrapper.generateQuad(ctx, self.memHandler)

    def exitAdd(self, ctx):
        if self.quadWrapper.topOperator() in [ADD, MINUS]:
            self.quadWrapper.generateQuad(ctx, self.memHandler)

    def exitMultModDiv(self, ctx):
        if self.quadWrapper.topOperator() in [MULT, MOD, DIV]:
            self.quadWrapper.generateQuad(ctx, self.memHandler)

    def getConstant(self, ctx):
        '''
        Helper to stringify "constant" rule
        
        Also pushes the constant's type & allocates it
        '''
        if ctx.CONST_BOOL() is not None:
            value = str(ctx.CONST_BOOL()) == 'true'
            self.quadWrapper.insertType(BOOL)
        elif ctx.CONST_I() is not None:
            value = int(str(ctx.CONST_I()))
            self.quadWrapper.insertType(INT)
        elif ctx.CONST_F() is not None:
            value = float(str(ctx.CONST_F()))
            self.quadWrapper.insertType(FLOAT)
        elif ctx.CONST_STR() is not None:
            value = str(ctx.CONST_STR())[1:-1]
            self.quadWrapper.insertType(STRING)
        else:
            self.quadWrapper.insertType(NONE)
            return NONE

        return self.memHandler.reserve(
            context=CONSTANT,
            dtype=tokenizeByValue(value),
            value=value
        )

    def validateCalledIds(self, ctx, is_function=False):
        '''
        Helper to validate id(s) being called.

        If [is_function] is set, then it verifies said function exists in the global
        context (or function context if being called by object). 
        '''
        ids = [str(id) for id in ctx.ID()]

        if len(ids) == 2:  # class attr/method being called (i.e. myobj.name or myobj.print())
            selfAccess = ids[0] == 'self'
            if selfAccess:
                class_name = self.ctxWrapper.getClassContext()
                if class_name is None:
                    raise error(ctx, SELF_USE_OUTSIDE_CLASS)
            else:
                class_var = self.ctxWrapper.getVariable(
                    ids[0],
                    context=self.ctxWrapper.top(),
                    insideClass=self.ctxWrapper.insideClass()
                )
                if class_var is None:
                    raise error(ctx, UNDEF_VAR.format(ids[0]))
                class_name = 'class ' + class_var['self'].type

            if is_function:
                method = self.ctxWrapper.getFunction(
                    ids[1], context=class_name)
                if method is None:
                    raise error(ctx, UNDEF_METHOD.format(ids[1], class_name))
                # Validate that we can access method (if outside class)
                if not selfAccess and method.access_type != PUBLIC:
                    raise error(ctx, NOT_PUBLIC_METHOD.format(
                        stringifyToken(method.access_type).upper(), ids[1], class_name))
            else:
                if selfAccess:  # Inside class method, use local memory
                    attr = self.ctxWrapper.getVariable(
                        ids[1], context=class_name)
                else:  # Accessing attribute outside class
                    attr = class_var.get(ids[1], None)
                if attr is None:
                    raise error(ctx, UNDEF_ATTRIBUTE.format(
                        ids[1], class_name))

                # Validate that we can access attribute (if outside class)
                if not selfAccess and attr.access_type != PUBLIC:
                    raise error(ctx, NOT_PUBLIC_ATTRIBUTE.format(
                        stringifyToken(attr.access_type).upper(), ids[1], class_name))

                self.quadWrapper.insertType(attr.type)
                self.quadWrapper.insertAddress(attr.address)
                if attr.isArray():
                    self.quadWrapper.insertDim(attr.address)

            return ids
        else:  # global var/func being called
            id = ids[0]
            if is_function:
                func = self.ctxWrapper.getFunctionIfExists(id)
                if func is None:
                    raise error(ctx, UNDEF_FUNC.format(id))
            else:
                var, _ = self.ctxWrapper.getVariableIfExists(id)
                if var is None:
                    raise error(ctx, UNDEF_VAR.format(id))

                id = var.address
                self.quadWrapper.insertType(var.type)
                self.quadWrapper.insertAddress(var.address)
                if var.isArray():
                    self.quadWrapper.insertDim(var.address)

            return id

    def enterVal(self, ctx):
        if ctx.unaryAddOp() is not None:
            self.quadWrapper.insertAddress(None)
            self.quadWrapper.insertType(NONE)

        if ctx.cond() is not None:  # nested cond
            # Add fake bottom to operator_stack
            self.quadWrapper.insertOperator(FALSEBOTTOM)
        elif len(ctx.ID()) > 0:  # identifier
            self.validateCalledIds(ctx)
        elif ctx.constant() is not None:  # const
            self.quadWrapper.insertAddress(self.getConstant(ctx.constant()))

    def exitVal(self, ctx):
        if self.quadWrapper.topOperator() in [POWER, UNARYADD, UNARYMINUS]:
            self.quadWrapper.generateQuad(ctx, self.memHandler)

    def enterBoolOp(self, ctx: PopurriParser.BoolOpContext):
        self.quadWrapper.insertOperator(ctx.getText())

    def enterCmpOp(self, ctx: PopurriParser.CmpOpContext):
        self.quadWrapper.insertOperator(ctx.getText())

    def enterAddOp(self, ctx: PopurriParser.AddOpContext):
        self.quadWrapper.insertOperator(ctx.getText())

    def enterMultDivOp(self, ctx: PopurriParser.MultDivOpContext):
        self.quadWrapper.insertOperator(ctx.getText())

    def enterAssignOp(self, ctx: PopurriParser.AssignOpContext):
        self.quadWrapper.insertOperator(ctx.getText())

    def enterExpOp(self, ctx: PopurriParser.ExpOpContext):
        self.quadWrapper.insertOperator(ctx.getText())

    def enterUnaryAddOp(self, ctx: PopurriParser.UnaryAddOpContext):
        op = ctx.getText()
        # Little hack since insertOperator tokenizes strings
        self.quadWrapper.insertOperator(UNARYADD if op == '+' else UNARYMINUS)

    def enterIndexation(self, ctx):
        self.quadWrapper.insertOperator(VERIFY)

    def exitIndexation(self, ctx):
        'Generates VERIFY quad, and handles address manipulation'
        # Need to check if the current array is using an ID as iterable.
        exp_result = self.quadWrapper.popAddress()
        array_var_starting_address = self.quadWrapper.popDim()

        var = self.ctxWrapper.getVariableByAddress(array_var_starting_address)

        # Create verify quad

        lInf = self.memHandler.reserve(
            context=CONSTANT,
            dtype=INT,
            value=0
        )

        lSup = self.memHandler.reserve(
            context=CONSTANT,
            dtype=INT,
            value=var.arraySize - 1
        )
        self.quadWrapper.insertQuad(Quadruple(
            op=self.quadWrapper.popOperator(),
            l=exp_result,
            r=lInf,  # arrays start at 0
            res=lSup))

        # Reserve memory for the literal address. Example: 5000 -> Int

        var_address_address = self.memHandler.reserve(
            context=CONSTANT,
            dtype=INT,
            value=var.address
        )

        tmp = self.memHandler.reserve(
            context=TEMPORAL,
            dtype=POINTER,
        )

        # create (exp_result + base address) quad

        self.quadWrapper.insertQuad(Quadruple(
            op=ADD,
            l=exp_result,
            r=var_address_address,
            res=tmp))
        self.quadWrapper.popAddress()
        self.quadWrapper.insertAddress(tmp)
        # Since the enterDeclaration is pushing a type no matter the variable being checked.
        # This pops the type and pushes the correct type
        self.quadWrapper.popType()
        # self.quadWrapper.insertType(var.type)

    def enterAssignment(self, ctx):
        self.inside_expression = True

    def exitAssignment(self, ctx):
        '''
        Generate ASSIGN quad to store right-hand value to left-hand address (if types match)
        It also handles shorthand operator assignment (+=, -=, etc.)
        '''
        if self.quadWrapper.topOperator() in [ASSIGN, ADDASSIGN, MINUSASSIGN, MULTASSIGN, DIVASSIGN, MODASSIGN]:
            res_address = self.quadWrapper.popAddress()
            var_address = self.quadWrapper.popAddress()
            res_type = self.quadWrapper.popType()
            var_type = self.quadWrapper.popType()

            var = None
            # Assign resulting type to variable and allocate in memory
            if var_type == NONE:
                var, _ = self.ctxWrapper.getVariableIfExists(var_address)
                var.type = res_type
                var.address = self.memHandler.reserve(
                    context=tokenizeContext(self.ctxWrapper.top()),
                    dtype=var.type
                )
                var_type = res_type
            # Var already has a defined type (and thus allocated)
            else:
                var = self.ctxWrapper.getVariableByAddress(var_address)

            op = self.quadWrapper.popOperator()
            if op is not ASSIGN:
                res_type = bailaMijaConElSeñor(
                    op - 1, var_type, res_type)
                if res_type is None:
                    raise error(ctx, TYPE_MISMATCH.format(
                        stringifyToken(op),
                        stringifyToken(var_type),
                        stringifyToken(res_type)
                    ))

            if var is not None:
                if var_type != res_type:
                    raise error(ctx, TYPE_MISMATCH.format(
                        stringifyToken(op),
                        stringifyToken(var_type),
                        stringifyToken(res_type)
                    ))

            self.quadWrapper.insertQuad(Quadruple(
                op=op,
                l=res_address,
                res=var.address if var is not None else var_address
            ))

    def enterFuncCall(self, ctx):
        '''
        Validates IDs being called (e.g. self.method(), obj.method() or myFunc())
        Generates ERAC quad to allocate class attributes (if class method is being called)
        And ERA quad to allocate function required memory
        '''
        ids = self.validateCalledIds(ctx, is_function=True)
        if len(ids) == 2:
            # Quad to allocate class in memory
            self.quadWrapper.insertQuad(Quadruple(
                op=ERAC,
                l=ids[0]
            ))
            ids = ids[1]

        # Quad to allocate function's required memory
        self.quadWrapper.insertQuad(Quadruple(
            op=ERA,
            l=ids
        ))

        self.quadWrapper.insertOperator(FALSEBOTTOM)
        self.param_count = 1

    def exitFuncCall(self, ctx):
        '''
        Validates function and call signatures match.
        Allocates return value if funcCall is being used in expression
        '''
        ids = [str(id) for id in ctx.ID()]

        # check funcCall by using the retrieved ids from call
        if len(ids) == 2:
            if ids[0] == 'self':
                class_name = self.ctxWrapper.getClassContext()
                if class_name is None:
                    raise error(ctx, SELF_USE_OUTSIDE_CLASS)
            else:
                class_var = self.ctxWrapper.getVariable(
                    ids[0],
                    context=self.ctxWrapper.top(),
                    insideClass=self.ctxWrapper.insideClass()
                )
                if class_var is None:
                    raise error(ctx, UNDEF_VAR.format(ids[0]))
                class_name = 'class ' + class_var['self'].type

            func = self.ctxWrapper.getFunction(
                ids[1], class_name)
        else:
            func = self.ctxWrapper.getFunctionIfExists(ids[0])

        if self.param_count - 1 != len(func.paramTypes):
            raise error(ctx, PARAM_AMOUNT_MISMATCH.format(
                func.id, len(func.paramTypes)))

        # Validate call signature with function signature
        # Note: Even though we can compare them directly, we still need to pop types from stack
        func_signature = func.paramTypes
        call_signature = self.quadWrapper.type_stack[-len(func_signature):]

        for func_ty in func_signature[::-1]:
            call_ty = self.quadWrapper.popType()
            if func_ty != call_ty:
                func_signature = tuple(map(stringifyToken, func_signature))
                call_signature = tuple(map(stringifyToken, call_signature))
                raise error(ctx, INVALID_SIGNATURE.format(
                    func.id, call_signature, func_signature))

        call = '.'.join(ids)

        self.quadWrapper.insertQuad(Quadruple(
            op=GOSUB,
            l=call
        ))

        # Allocate return value if using funcCall in expression (and if function returns something)
        if self.inside_expression:
            # Trying to use void function inside expression
            if func.return_type == NONE:
                raise error(
                    ctx, VOID_FUNCTION_CALL_ON_EXPRESSION.format(func.id))

            tmp = self.memHandler.reserve(
                context=TEMPORAL,
                dtype=func.return_type
            )

            self.quadWrapper.insertQuad(Quadruple(
                op=ASSIGN,
                l=call,
                res=tmp
            ))
            self.quadWrapper.insertAddress(tmp)
            self.quadWrapper.insertType(func.return_type)

        # Reset parameter counter flag (So we dont add func quad when exiting a condition)
        self.param_count = -1

    def enterConstant(self, ctx):
        pass

    def exitConstant(self, ctx):
        pass

    def enterConst_arr(self, ctx):
        pass

    def exitConst_arr(self, ctx):
        pass

    def handlePrint(self, PRINT_OP):
        '''
        Generates print quadruples from cond parameters
        '''
        print_quads = []
        while True:
            address = self.quadWrapper.popAddress()
            if address is None or address == FALSEBOTTOM:
                break

            self.quadWrapper.popType()
            print_quads.append(Quadruple(
                op=PRINT_OP,
                res=address
            ))

        if not print_quads:
            self.quadWrapper.insertQuad(Quadruple(PRINT_OP))

        # Quads are generated in inverse order (due to being in stack), so push them end to start
        for quad in print_quads[::-1]:
            self.quadWrapper.insertQuad(quad)

    def enterPrintStmt(self, ctx):
        '''
        [PrintStmt] this is the first part of PrintStmt
        '''
        self.quadWrapper.insertAddress(FALSEBOTTOM)
        self.inside_expression = True

    def exitPrintStmt(self, ctx):
        '''
        [PrintStmt] this is the second part of PrintStmt
        '''
        self.handlePrint(PRINT)

    def enterPrintlnStmt(self, ctx):
        '''
        [PrintlnStmt] this is the first part of PrintlnStmt
        '''
        self.enterPrintStmt(ctx)  # Same as print

    def exitPrintlnStmt(self, ctx):
        '''
        [PrintlnStmt] this is the second part of PrintlnStmt
        '''
        self.handlePrint(PRINTLN)

    def enterInputStmt(self, ctx):
        '''
        [InputStmt] this is the first part of InputStmt
        '''
        self.validateCalledIds(ctx)
        self.quadWrapper.insertQuad(Quadruple(
            op=INPUT,
            res=self.quadWrapper.popAddress()
        ))

    def exitInputStmt(self, ctx):
        pass

    def enterCondParam(self, ctx):
        pass

    def exitCondParam(self, ctx):
        pass

    def enterFuncParams(self, ctx):
        '''
        [FuncParams] this is the first part of FuncParams

        all parameters entered in function declaration will be handled
        in this function. Memory assignation and var table entry generation
        is part of the process.

        '''
        no_params = len(ctx.ID())
        for i in range(no_params):
            param = Variable(
                id=ctx.ID(i),
                type=ctx.TYPE(i),
                paramNo=i + 1
            )
            param.address = self.memHandler.reserve(
                context=LOCAL,
                dtype=param.type
            )
            self.ctxWrapper.addVariable(
                param,
                context=self.ctxWrapper.top(),
                insideClass=self.ctxWrapper.insideClass()
            )

        pass

    def exitFuncParams(self, ctx):
        pass
