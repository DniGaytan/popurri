from PopurriListener import ContextWrapper, QuadWrapper, Variable, Function, pprint
from memory import MemoryHandler, MemoryContext
from popurri_tokens import *
from error_tokens import *
from operator import *
import json
from copy import deepcopy


def importMemory(f):
    'This function imports the pre-allocated memory of the parsed .pop file'
    memHandler = MemoryHandler()
    mem_dict = json.loads(f.readline())
    for ctx, mem in mem_dict.items():
        memObj = MemoryContext(mem['start'], mem['max_size'])
        for section, spaces in mem['sections'].items():
            memObj.sections[int(section)] = spaces

        memHandler.contexts[int(ctx)] = memObj

    return memHandler


def importContext(f):
    '''
    This function imports the varTable and funcTable from the given file.
    And due to its dictionary structure, it's parsed thoroughly to re-construct it
    whilst using the Variable and Funtion constructors.
    It returns a ContextWrapper object which contains both structures
    '''
    # Import Variables
    vars = json.loads(f.readline())
    for ctx in vars.values():  # Iterate over contexts
        for k, v in ctx.items():
            if 'func ' in k or 'self' in v:  # Inside method/object varTable
                for vid, vdict in v.items():
                    if 'self' in vdict:  # Var is object, iterate over attributes
                        for attrid, attrdict in vdict.items():
                            if 'self' == attrid:
                                class_id = attrdict['type']
                                attrdict['type'] = NONE
                            vdict[attrid] = Variable(**attrdict)
                            if 'self' == attrid:
                                vdict[attrid].type = class_id
                    else:
                        if 'self' == vid:
                            class_id = vdict['type']
                            vdict['type'] = NONE
                        v[vid] = Variable(**vdict)
                        if 'self' == vid:
                            v[vid].type = class_id
            else:
                ctx[k] = Variable(**v)

    # Import Functions
    funcs = json.loads(f.readline())
    for ctx in funcs.values():
        for fid, fdict in ctx.items():
            ctx[fid] = Function(**fdict)

    return ContextWrapper(variables=vars, functions=funcs)


# Maps Popurri tokens to their respective python function
opMap = {
    ADD: add,
    MINUS: sub,
    MULT: mul,
    DIV: truediv,
    MOD: mod,
    POWER: pow,
    EQUAL: eq,
    NOTEQUAL: ne,
    GREATER: gt,
    GREATEREQ: ge,
    LESSER: lt,
    LESSEREQ: le,
    UNARYADD: pos,
    UNARYMINUS: neg,
}


def handleBinaryOperation(memHandler, op, l_val, r_val, res):
    'applies the binary operator function specified by opMap and stores it in the result address'
    opFunc = opMap[op]
    memHandler.update(res, opFunc(l_val, r_val))


def handleUnaryOperation(memHandler, op, r_val, res):
    'applies the unary operator function specified by opMap and stores it in the result address'
    opFunc = opMap[op]
    memHandler.update(res, opFunc(r_val))


def run(obj_file):
    '''
    This function accepts a .pobj (Popurri Object Code file), and it imports the following structures:
        - Variable Table
        - Function Table
        - Memory Handler
        - List of quadruples to execute
    And executes said quadruples using the formerly mentioned structures
    '''
    with open(obj_file, 'r') as f:
        ctx = importContext(f)
        memHandler = importMemory(f)
        quads = json.loads(f.readline())

    # Reutilizing the ctx_stack in this wrapper to handle memory stacks
    memCtxWrapper = ContextWrapper()
    memCtxWrapper.pop()  # Remove global context
    # Flag
    method_call = False
    original_method_caller = None
    # Instruction Pointer
    ip = 0
    ip_stack = []
    while ip < len(quads):
        quad = quads[ip]

        op, l, r, res = quad
        if type(l) == int:
            l_val = memHandler.getValue(l)
        if type(r) == int:
            r_val = memHandler.getValue(r)

        # GOTOs
        if op == GOTO:
            if not res:
                return

            ip = res - 1
            continue
        elif (op == GOTOF and l_val == False or
              op == GOTOV and l_val == True):
            ip = res - 1
            continue

        # Operations
        elif op == ASSIGN:
            if type(l) == str:  # l is a return value from a function
                func_name = 'func ' + l.split('.')[-1]
                return_var = ctx.getVariable(func_name)
                l_val = memHandler.getValue(return_var.address)

                # Remove return value from memory & global varTable
                del ctx.variables['global'][func_name]
                memHandler.contexts[GLOBAL].sections[return_var.type].pop()

            if type(l_val) == int and l_val >= 28000 and l_val <= 30000:
                val_type = memHandler.getAddressType(l_val)
                if val_type == POINTER:
                    l_val = memHandler.getValue(l_val)
            if type(res) == int and res >= 28000 and res <= 30000:
                res_type = memHandler.getAddressType(res)
                if res_type == POINTER:
                    res = memHandler.getValue(res)
            memHandler.update(res, l_val)
        elif op in [ADD, MINUS, MULT, DIV, MOD, POWER, EQUAL, NOTEQUAL, GREATER, GREATEREQ, LESSER, LESSEREQ]:
            handleBinaryOperation(memHandler, op, l_val, r_val, res)
        elif op in [UNARYADD, UNARYMINUS]:
            handleUnaryOperation(memHandler, op, r_val, res)
        elif op == ANDOP:  # For some reason these arent implemented in operator pkg, so do them manually
            memHandler.update(res, l_val and r_val)
        elif op == OROP:
            memHandler.update(res, l_val or r_val)
        elif op in [ADDASSIGN, MINUSASSIGN, MULTASSIGN, DIVASSIGN, MODASSIGN]:
            res_val = memHandler.getValue(res)
            # Move token one pos up, so ADDASSIGN -> ADD, MINUSASSIGN -> MINUS, etc.
            op -= 1
            # Applies short-hand operator and stores it in res
            handleBinaryOperation(memHandler, op, res_val, l_val, res)

        # Special Functions
        elif op == INPUT:
            res_type = memHandler.getAddressType(res)

            if type(res) == int and res >= 28000 and res <= 30000:
                res_type = memHandler.getAddressType(res)
                if res_type == POINTER:
                    res = memHandler.getValue(res)
                    res_type = memHandler.getAddressType(res)
            tmp = input()
            try:
                if res_type == INT:
                    tmp = int(tmp)
                elif res_type == FLOAT:
                    tmp = float(tmp)
                elif res_type == BOOL:
                    tmp = tmp == 'true'
                # Input is casted to string by default, so no need to cast
            except Exception:
                raise Exception(CANNOT_CAST.format(
                    tmp, stringifyToken(res_type)))

            memHandler.update(res, tmp)
        elif op == PRINT or op == PRINTLN:
            if res >= 28000 and res <= 30000:  # POINTER
                res = memHandler.getValue(res)
            print(memHandler.getValue(res), end=' ' if op == PRINT else '\n')

        # Classes
        elif op == ERAC:
            # Push function's memory ctx to stack
            memCtxWrapper.push(memHandler)
            func_mem = memCtxWrapper.top()
            # Flush allocated values from memory, but keep count of how many have been allocated
            for context in [LOCAL, TEMPORAL]:
                func_mem.flush(context)
                func_mem.contexts[context].allocations = memHandler.contexts[context].allocations

            if l == 'self':  # Recursive class call
                class_var = ctx.getAttributes(ctx.getClassContext())
                ctx.push(ctx.getClassContext())
            else:
                class_var = ctx.getVariable(
                    l,
                    context=ctx.top(),
                    insideClass=ctx.top() != 'global'
                )
                ctx.push('class ' + class_var['self'].type)
                original_method_caller = l

            for attr in class_var.values():
                if attr.id == 'self':  # this attribute only contains the class name
                    continue

                attr_val = memHandler.getValue(attr.address)
                func_mem.reserve(
                    context=LOCAL,
                    dtype=attr.type,
                    value=attr_val
                )
                if attr.isArray():  # Allocate array slots
                    for i in range(attr.arraySize):
                        slot_val = memHandler.getValue(attr.address + i)
                        func_mem.reserve(
                            context=LOCAL,
                            dtype=attr.type,
                            value=slot_val
                        )

            method_call = True  # Set flag so ERA quad doesnt flush mem

        # Function Calls
        elif op == ERA:
            # Push memory ctx to stack (if calling a regular function)
            if not method_call:
                memCtxWrapper.push(memHandler)
                func_mem = memCtxWrapper.top()
                # Flush allocated values from memory, but keep count of how many have been allocated
                for context in [LOCAL, TEMPORAL]:
                    func_mem.flush(context)
                    func_mem.contexts[context].allocations = memHandler.contexts[context].allocations
            else:
                func_mem = memCtxWrapper.top()

            ctx.push('func ' + l)
            func = ctx.getCurrentFunction()

            # Allocate required function memory
            ctxs = [LOCAL, TEMPORAL]
            dtypes = [INT, FLOAT, BOOL, STRING, POINTER]
            for i, era in enumerate([func.era_local, func.era_tmp]):
                for j, type_allocations in enumerate(era):
                    for _ in range(type_allocations):
                        func_mem.reserve(
                            context=ctxs[i],
                            dtype=dtypes[j],
                        )

            method_call = False  # Reset flag
        elif op == PARAM:
            if ctx.insideClass():
                params = ctx.variables[ctx.getClassContext()][ctx.top()]
            else:
                params = ctx.variables[ctx.top()]

            # Update the local param address with the passed value
            paramNo = int(res.split(' ')[1])  # res is formatted as 'param N'
            for param in params.values():
                if param.paramNo == paramNo:
                    func_mem = memCtxWrapper.top()
                    func_mem.update(
                        address=param.address,
                        value=l_val,
                    )
                    break

        elif op == GOSUB:
            func_id = l.split('.')[-1]
            func_ctx = ctx.getClassContext() if ctx.insideClass() else 'global'
            func = ctx.getFunction(func_id, func_ctx)
            if func.quads_range != (-1, -1):
                # Gonna return to this ip when returning from func
                ip_stack.append(ip + 1)
                # Go to function start
                ip = func.quads_range[0] - 1
                # Sleep current context
                tmp = memHandler
                memHandler = memCtxWrapper.pop()
                memCtxWrapper.push(tmp)
                continue

        elif op == GOTOR:
            prev_ctx = memCtxWrapper.pop()
            # Allocate return value as global with func name
            return_dtype = memHandler.getAddressType(res)
            return_var = Variable(
                id=ctx.top(),
                type=return_dtype
            )
            return_var.address = prev_ctx.reserve(
                context=GLOBAL,
                dtype=return_dtype,
                value=memHandler.getValue(res)
            )
            # And add it to global varTable
            ctx.addVariable(return_var)

            # Return to previous context
            ip = ip_stack.pop()
            memHandler = prev_ctx

            # Pop function/method context
            ctx.pop()
            if 'class ' in ctx.top():
                ctx.pop()
            continue

        elif op == ENDPROC:
            prev_ctx = memCtxWrapper.pop()
            # If inside class, copy over attributes (in case they were modified)
            if ctx.insideClass():
                class_var = ctx.getAttributes(ctx.getClassContext())

                if len(ctx.context_stack) > 3:  # Inside nested call
                    for attr in class_var.values():
                        if attr.id == 'self':  # this attribute only contains the class name
                            continue

                        # Pass attribute value to returning context
                        updated_val = memHandler.getValue(attr.address)
                        prev_ctx.update(
                            attr.address,  # Since we're returning to another local context, address will be the same
                            updated_val
                        )
                        # If attribute is an array, pass over the rest of its values as well
                        if attr.isArray():
                            for i in range(1, attr.arraySize):
                                updated_val = memHandler.getValue(
                                    attr.address + i)
                                prev_ctx.update(attr.address + i, updated_val)
                else:  # Passing attributes to global context
                    obj_var = ctx.getVariable(original_method_caller)
                    for attr in class_var.values():
                        if attr.id == 'self':  # this attribute only contains the class name
                            continue

                        # Pass attribute value to returning context
                        updated_val = memHandler.getValue(attr.address)
                        prev_ctx.update(
                            obj_var[attr.id].address,
                            updated_val
                        )
                        # If attribute is an array, pass over the rest of its values as well
                        if attr.isArray():
                            for i in range(1, attr.arraySize):
                                updated_val = memHandler.getValue(
                                    attr.address + i)
                                prev_ctx.update(
                                    obj_var[attr.id].address + i, updated_val)

            # Return to previous context
            ip = ip_stack.pop()
            memHandler = prev_ctx

            func = ctx.getFunction(
                ctx.top(),
                context=ctx.getClassContext() if ctx.insideClass() else 'global'
            )
            # Allocate return var if nothing has been returned
            if ctx.getVariable(ctx.top()) is None and func.return_type is not NONE:
                return_var = Variable(
                    id=ctx.top(),
                    type=func.return_type
                )
                return_var.address = memHandler.reserve(
                    context=GLOBAL,
                    dtype=func.return_type
                )
                ctx.addVariable(return_var)

            # Pop function/method context
            ctx.pop()
            if 'class ' in ctx.top():
                ctx.pop()

            continue

        elif op == VERIFY:
            index = l_val
            lInf = r_val
            lSup = memHandler.getValue(res)

            if index < lInf or index > lSup:
                raise Exception(OUT_OF_RANGE.format(index))

        ip += 1
