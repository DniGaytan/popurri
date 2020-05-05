from antlr4 import *
from parser.PopurriParser import PopurriParser
from popurri_tokens import *
from semantic_cube import bailaMijaConElSeñor
import jsbeautifier as js
import json


def pprint(*args):
    opts = js.default_options()
    opts.indent_size = 2
    for arg in args:
        print(js.beautify(json.dumps(arg, default=vars), opts))


class QuadWrapper():
    '''
    Si tienes un mejor nombre para esta clase, go ahead.
    '''
    operator_codes = ['', '+', '+=', '-', '-=', '*', '*=', '/', '/=',
                      '%', '%=', '**', 'is', 'is not', '>', '>=', '<',
                      '<=', 'and', 'or', '=', 'print']

    def __init__(self):
        self.tmp_counter = 0
        self.quads = []
        self.quads_ptr = 0
        self.type_stack = []
        self.operator_stack = []
        self.paren_stack = []
        self.address_stack = []
        self.jump_stack = []

    def insertQuad(self, quad, at=None):
        self.quads_ptr += 1
        if at is not None:
            self.quads.insert(at, quad.__str__())
        else:
            self.quads.append(quad.__str__())

    def fillQuadWith(self, filler, at):
        new_quad = list(self.quads[at])
        new_quad[3] = filler
        self.quads[at] = tuple(new_quad)

    def topParen(self):
        return self.paren_stack[-1] if len(self.paren_stack) > 0 else 0

    def topOperator(self):
        return self.operator_stack[-1] if len(self.operator_stack) - self.topParen() > 0 else None

    def topJump(self):
        return self.jump_stack[-1] if len(self.jump_stack) > 0 else None

    def popOperator(self):
        return self.operator_stack.pop() if len(self.operator_stack) - len(self.paren_stack) > 0 else None

    def popAddress(self):
        return self.address_stack.pop() if len(self.address_stack) > 0 else None

    def popJump(self):
        return self.jump_stack.pop() if len(self.jump_stack) > 0 else None

    def popType(self):
        return self.type_stack.pop() if len(self.type_stack) > 0 else None

    def popParen(self):
        return self.paren_stack.pop() if len(self.paren_stack) > 0 else 0

    def insertParen(self):
        self.paren_stack.append(len(self.operator_stack))

    def insertType(self, type):
        self.type_stack.append(str(type))

    def insertAddress(self, address):
        self.address_stack.append(str(address))

    def insertOperator(self, operator):
        self.operator_stack.append(operator)

    def insertJump(self, jump=None):
        self.jump_stack.append(self.quads_ptr if jump is None else jump)

    def getTokenCode(self, element):
        return self.operator_codes.index(element) + 1

    def validateTypes(self):
        op = self.topOperator()
        r_type = self.popType()
        l_type = self.popType()
        res_type = bailaMijaConElSeñor(op, l_type, r_type)
        if res_type is None:
            raise Exception(f'Unsupported operand types for {op}: "{l_type}" and "{r_type}"')
        # Push resulting type into stack
        self.insertType(res_type)

    def handleQuadruple(self, operators):
        if self.topOperator() in operators:
            self.validateTypes()

            self.tmp_counter += 1
            tmp = f'temp_{self.tmp_counter}'
            self.insertQuad(Quadruple(
                op=self.popOperator(),
                r=self.popAddress(),
                l=self.popAddress(),
                res=tmp
            ))
            self.insertAddress(tmp)
            return True


class Quadruple():

    def __init__(self, op, l=None, r=None, res=None):
        self.op = op
        # Arguments (In some cases one of both of them would be -1 indicating there is no value)
        self.l = l
        self.r = r
        # Where result of op(l, r) is stored
        # This is an address rather than a value
        self.res = res

    def __str__(self):
        return (self.op, self.l, self.r, self.res)


class GlobalContext():
    '''
    Esta es una tabla de procedimientos
    Antes FuncTable
    '''

    def __init__(self):
        self.variables = {}
        self.functions = {}

    def getVariable(self, var_id, context="global"):
        if context in self.variables:
            return self.variables[context].get(str(var_id), None)
        else:
            return None

    def getFunction(self, func_id, context="global"):
        if context in self.functions:
            return self.functions[context].get(str(func_id), None)
        else:
            return None

    def addVariable(self, var, context="global"):
        if context in self.variables:
            self.variables[context][var.id] = var
        else:
            self.variables[context] = {
                var.id: var
            }

    def addFunction(self, func, context="global"):
        if context in self.functions:
            self.functions[context][func.id] = func
        else:
            self.functions[context] = {
                func.id: func
            }

    def varExistsInContext(self, var_id, ctx_id):
        if ctx_id not in self.variables:
            return False

        return self.variables[ctx_id].get(str(var_id), False)

    def functionExistsInContext(self, func_id, ctx_id):
        if ctx_id not in self.functions:
            return False

        return self.functions[ctx_id].get(str(func_id), False)

    def classExists(self, id):
        id = str(id)
        if 'class' not in id:
            id = 'class ' + id

        return id in self.variables or id in self.functions


class Variable():
    '''
    Esto nos permite simular la creacion de variables. Inicializandolas con atributos predeterminados.
    [id] es el identificador con el que se podra localizar la actual variable. Ej. var edad : int. Donde edad es el ID.
    [type] es el tipo de dato con el que la variable estara relacionada. Ej. var edad : int. Donde int es el tipo de dato.
    [value] es el valor inicial que tendra la variable. Ej. var edad = 25. Donde 25 es el valor inicial.
    '''

    def __init__(self, id, access_type="public", type=None, value=None):
        self.access_type = str(access_type)
        self.id = str(id)
        self.type = str(type)
        self.value = value


class Object():
    '''
    Esto nos permite simular la creacion de clases. Inicializandolos con atributos predeterminados.
    [id] es el identificador con el que se podra localizar la clase actual. Ej. class Humano {}. Donde Humano es el identificador.
    [parent_id] es el identificador del cual la clase actual heredara todas las propiedades. Ej. class Humano -> Persona. Donde Humano es el identificador
    padre.
    '''

    def __init__(self, id, parent_id=None):
        self.id = str(id)
        self.parent_id = str(parent_id)


class Function():
    '''
    Esto nos permite simular la creacion de funciones. Inicializandolas con atributos predeterminados.
    [id] es el identificador con el que se podra localizar la funcion actual. Ej. func habla() {}. Donde habla es el identificador.
    [return_type] es el tipo de dato que regresara la funcion al terminar su ejecucion. Void es el tipo predeterminado.
    '''

    def __init__(self, id, return_type="void", access_type="public"):
        self.id = str(id)
        self.return_type = str(return_type)
        self.access_type = str(access_type)


class PopurriListener(ParseTreeListener):
    '''
    -Esta clase nos permite simular la creacion de tabla de variables
    -[Tal vez podamos usar esta clase para simular la semantica basica de expresiones]
    -Cada funcion 'enter' representa el estado cuando se inicia una  regla
    -Cada funcion 'exit' representa el estado cuando se acaba una regla
    '''

    def __init__(self):
        self.global_ctx = GlobalContext()
        self.quadWrapper = QuadWrapper()
        self.if_cond = False
        self.current_ctx = 'global'

    def enterProgram(self, ctx):
        '''
        [Program] marca el inicio de las reglas de la gramatica. Aqui inicia la fase de compilacion.
        '''
        pass

    def exitProgram(self, ctx):
        '''
        [Program] marca el final de las reglas de la gramatica. Aqui termina la fase de compilacion.
        '''
        print("--VARIABLES--")
        pprint(self.global_ctx.variables)
        print("--FUNCTIONS--")
        pprint(self.global_ctx.functions)

        print('quads_stack = [')
        for i, x in enumerate(self.quadWrapper.quads, start=1):
            print('\t',i, x)
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
        pass

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
        pass

    def exitDeclarations(self, ctx):
        pass

    def enterDeclaration(self, ctx):
        # Checks if global is already declared
        if self.global_ctx.varExistsInContext(ctx.ID(0), "global"):
            raise f'ERROR VAR {str(ctx.ID(0))} ALREADY DEFINED'

        var = None
        # var has data_type : INT, FLOAT, STRING, BOOL
        # TODO: Arrays are not yet implemented
        if ctx.TYPE() is not None:
            var = Variable(
                id=ctx.ID(0),
                type=ctx.TYPE()
            )
        # var is type object
        else:
            class_name = str(ctx.ID(1))
            if not self.global_ctx.classExists(class_name):
                raise Exception(f'ERROR UNDEFINED CLASS TYPE {class_name}')

            var = Variable(
                id=ctx.ID(0),
                type=class_name
            )

        self.global_ctx.addVariable(var)

    def exitDeclaration(self, ctx):
        pass

    def createFunction(self, ctx):
        func = Function(
            id=ctx.ID(0)
        )
        # Function has params
        if ctx.funcParams() is not None:
            no_params = len(ctx.funcParams().ID())
            for i in range(no_params):
                param = Variable(
                    id=ctx.funcParams().ID(i),
                    type=ctx.funcParams().TYPE(i),
                )
                self.global_ctx.addVariable(param, func.id)

        # Function has primitive return type
        if ctx.TYPE() is not None:
            func.return_type = str(ctx.TYPE())
        # Function returns object
        elif len(ctx.ID()) > 1:
            func.return_type = str(ctx.ID(1))

        return func

    def enterFunction(self, ctx):
        if self.global_ctx.functionExistsInContext(ctx.ID(0), "global"):
            raise f'ERROR RE-DEFINITION OF {str(ctx.ID(0))}'

        func = self.createFunction(ctx)
        self.global_ctx.addFunction(func)
        self.current_ctx = func.id
        pass

    def exitFunction(self, ctx):
        self.current_ctx = 'global'
        pass

    def getAccessType(self, ctx):
        ty = ctx.ACCESS_TYPE()
        return 'public' if ty is None else ty

    def enterClassDeclaration(self, ctx):
        class_name = str(ctx.ID())
        if self.global_ctx.classExists(class_name):
            raise f'ERROR RE-DEFINITION OF {class_name}'

        self.current_ctx = 'class ' + class_name
        klass = Object(
            id=class_name
        )
        if ctx.parent() is not None:
            klass.parent_id = 'class ' + str(ctx.parent().ID())
            if not self.global_ctx.classExists(klass.parent_id):
                raise 'ERROR PARENT CLASS MUST BE DEFINED BEFORE CHILD CLASS'

            # Inherit attributes
            for attribute in self.global_ctx.variables[klass.parent_id].values():
                if attribute.access_type != 'private':
                    self.global_ctx.addVariable(attribute, 'class ' + klass.id)

            # Inherit functions
            for func in self.global_ctx.functions[klass.parent_id].values():
                if func.access_type != 'private':
                    self.global_ctx.addFunction(func, 'class ' + klass.id)

        # Parse class attributes
        for declarations in ctx.attributes():
            access_type = self.getAccessType(declarations)

            for attr in declarations.attribute():
                # if attribute inherited, do nothing
                if self.global_ctx.varExistsInContext(attr.ID(), klass.parent_id):
                    continue
                # Checks if attribute is already declared within class
                elif self.global_ctx.varExistsInContext(attr.ID(), 'class ' + klass.id):
                    raise f'ERROR ATTRIBUTE {str(attr.ID())} ALREADY DEFINED'

                var = Variable(
                    id=attr.ID(),
                    type=attr.TYPE(),
                    access_type=access_type
                )
                self.global_ctx.addVariable(var, 'class ' + klass.id)

        # Parse class methods
        for method in ctx.method():
            # if attribute inherited, do nothing
            if self.global_ctx.functionExistsInContext(attr.ID(), klass.parent_id):
                continue
            # Checks if attribute is already declared within class
            elif self.global_ctx.functionExistsInContext(method.ID(0), 'class ' + klass.id):
                raise f'ERROR METHOD {str(attr.ID())} ALREADY DEFINED'

            access_type = self.getAccessType(method)

            method = self.createFunction(method) # TODO fix how params are generated in varTable for object methods
            method.access_type = str(access_type)

            self.global_ctx.addFunction(method, 'class ' + klass.id)

        pass

    def exitClassDeclaration(self, ctx):
        self.current_ctx = 'global'
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
        pass

    def exitMethod(self, ctx):
        pass

    def enterStatement(self, ctx):
        self.if_cond = False
        pass

    def exitStatement(self, ctx):
        pass

    def enterWhileLoop(self, ctx):
        self.if_cond = True
        self.quadWrapper.insertJump()
        pass

    def exitWhileLoop(self, ctx):
        goto_quad = Quadruple('GOTO')
        self.quadWrapper.insertQuad(goto_quad)

        # Fill while gotoF with next quad outside loop
        self.quadWrapper.fillQuadWith(
            self.quadWrapper.quads_ptr + 1,
            at=self.quadWrapper.popJump()
        )
        # Fill goto with loop start
        self.quadWrapper.fillQuadWith(
            self.quadWrapper.popJump() + 1,
            at=self.quadWrapper.quads_ptr - 1
        )

    def enterForLoop(self, ctx):
        pass

    def exitForLoop(self, ctx):
        pass

    def enterBranch(self, ctx):
        self.quadWrapper.insertJump('(')
        pass

    def exitBranch(self, ctx):
        self.if_cond = False
        while True:
            jump = self.quadWrapper.popJump()
            if jump is '(' or jump is None:
                break

            self.quadWrapper.fillQuadWith(
                self.quadWrapper.quads_ptr + 1,
                at=jump
            )

    def enterIfStmt(self, ctx):
        self.if_cond = True

    def exitIfStmt(self, ctx):
        # Rellena el GOTOF de este mismo IF con el siguiente cuadruplo
        self.quadWrapper.fillQuadWith(
            self.quadWrapper.quads_ptr + 2,
            at=self.quadWrapper.popJump()
        )

        # Anade un GOTO al final del IF
        goto_quad = Quadruple('GOTO')

        self.quadWrapper.insertJump()
        self.quadWrapper.insertQuad(goto_quad)

    def enterElseIf(self, ctx):
        self.if_cond = True

    def exitElseIf(self, ctx):
        self.quadWrapper.fillQuadWith(
            self.quadWrapper.quads_ptr + 2,
            at=self.quadWrapper.popJump(),
        )

        # Anade un GOTO al final del ELSE IF
        goto_quad = Quadruple('GOTO')

        self.quadWrapper.insertJump()
        self.quadWrapper.insertQuad(goto_quad)

    def enterElseStmt(self, ctx):
        pass

    def exitElseStmt(self, ctx):
        self.quadWrapper.fillQuadWith(
            self.quadWrapper.quads_ptr + 1,
            at=self.quadWrapper.popJump()
        )
        pass

    def enterReturnStmt(self, ctx):
        pass

    def exitReturnStmt(self, ctx):
        pass

    def exitCond(self, ctx):
        self.quadWrapper.popParen()
        if self.if_cond:
            if_quad = Quadruple('GOTOF', l=self.quadWrapper.address_stack.pop())
            self.quadWrapper.insertJump()
            self.quadWrapper.insertQuad(
                if_quad,
                at=self.quadWrapper.quads_ptr
            )

    def exitCmp(self, ctx):
        self.quadWrapper.handleQuadruple(['and', 'or'])

    def exitExp(self, ctx):
        self.quadWrapper.handleQuadruple(['<', '<=', '>', '>=', 'is', 'is not'])

    def exitAdd(self, ctx):
        self.quadWrapper.handleQuadruple(['+', '-'])

    def exitMultModDiv(self, ctx):
        self.quadWrapper.handleQuadruple(['*', '/', '%'])

    # Helper to stringify 'constant' rule
    def getConstant(self, ctx):
        if ctx.CONST_BOOL() is not None:
            self.quadWrapper.insertType('bool')
            return str(ctx.CONST_BOOL())
        elif ctx.CONST_I() is not None:
            self.quadWrapper.insertType('int')
            return str(ctx.CONST_I())
        elif ctx.CONST_F() is not None:
            self.quadWrapper.insertType('float')
            return str(ctx.CONST_F())
        elif ctx.CONST_STR() is not None:
            self.quadWrapper.insertType('string')
            return str(ctx.CONST_STR())
        else:
            self.quadWrapper.insertType('none')
            return 'none'
        # TODO: add arrays

    def validateIds(self, ids):
        ids = [str(id) for id in ids]

        if len(ids) is 2: # class attribute being accessed (i.e. myvar.myattribute)
            class_var = self.global_ctx.getVariable(ids[0])
            if class_var is None:
                raise Exception(f'USE OF UNDEFINED VARIABLE "{ids[0]}"')

            attribute = self.global_ctx.getVariable(ids[1], 'class ' + class_var.type)
            if attribute is None:
                raise Exception(f'TRYING TO ACCESS UNDEFINED ATTRIBUTE "{ids[1]}" FROM CLASS "{class_var.type}"')

            if attribute.access_type is not 'public':
                raise Exception(f'TRYING TO ACCESS {attribute.access_type.upper()} ATTRIBUTE "{ids[1]}" FROM CLASS "{class_var.type}"')

             # Both variable and attribute exist!
            self.quadWrapper.insertType(attribute.type)
            return '.'.join(ids)
        else: # variable being accessed
            # Check local context first (if applicable)
            if self.current_ctx is not 'global':
                var = self.global_ctx.getVariable(ids[0], self.current_ctx)
                if var is not None:
                    self.quadWrapper.insertType(var.type)
                    return ids[0]

            # Check global context (if not found or n/a)
            var = self.global_ctx.getVariable(ids[0])
            if var is None:
                raise Exception(f'USE OF UNDEFINED VARIABLE "{ids[0]}"')

            self.quadWrapper.insertType(var.type)
            return ids[0]


    def enterVal(self, ctx):
        if ctx.cond() is not None: # nested cond
            # Add fake bottom to operator_stack
            self.quadWrapper.insertParen()
        elif len(ctx.ID()) > 0:  # identifier
            id = self.validateIds(ctx.ID())
            self.quadWrapper.insertAddress(id)
        elif ctx.constant() is not None: # const
            self.quadWrapper.insertAddress(self.getConstant(ctx.constant()))

        # TODO implement arrays

    def exitVal(self, ctx):
        self.quadWrapper.handleQuadruple(['**'])

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

    def enterExpOp(self, ctx:PopurriParser.ExpOpContext):
        self.quadWrapper.insertOperator(ctx.getText())

    def enterIndexation(self, ctx):
        pass

    def exitIndexation(self, ctx):
        pass

    def enterAssignment(self, ctx):
        pass

    def exitAssignment(self, ctx):
        if self.quadWrapper.topOperator() in ['=', '+=', '-=', '*=', '/=', '%=']:
            var_id = self.validateIds(ctx.ID())
            var_type = self.quadWrapper.popType()
            op = self.quadWrapper.popOperator()
            res_type = self.quadWrapper.popType()
            if op is not '=':
                res_type = bailaMijaConElSeñor(op[0], var_type, res_type)
                if res_type is None:
                    raise Exception(f'Unsupported operand types for {op}: "{var_type}" and "{res_type}"')

            if var_type != res_type:
                raise Exception(f'Type mismatch: cannot put value of type {res_type} into "{var_id}" (type {var_type})')

            self.quadWrapper.insertQuad(Quadruple(
                op=op,
                l=self.quadWrapper.popAddress(),
                res=var_id
            ))
        pass

    def enterFuncCall(self, ctx):
        pass

    def exitFuncCall(self, ctx):
        pass

    def enterConstant(self, ctx):
        pass

    def exitConstant(self, ctx):
        pass

    def enterConst_arr(self, ctx):
        pass

    def exitConst_arr(self, ctx):
        pass

    def enterIterable(self, ctx):
        pass

    def exitIterable(self, ctx):
        pass

    def enterPrintStmt(self, ctx):
        pass

    def exitPrintStmt(self, ctx):
        pass

    def enterInputStmt(self, ctx):
        pass

    def exitInputStmt(self, ctx):
        pass

    def enterCondParam(self, ctx):
        pass

    def exitCondParam(self, ctx):
        pass

    def enterFuncParams(self, ctx):
        pass

    def exitFuncParams(self, ctx):
        pass
