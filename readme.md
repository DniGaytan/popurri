# Lenguaje de programacion - Popurrí

Popurrí es un lenguaje creado con el fin de simular la experiencia de un lenguaje orientado a objetos. Sin embargo, no todo termina ahi; el equipo de desarrollo opto por juntar caracteristicas populares y comodas de otros lenguajes e implementar sus beneficios y estetica en el lenguaje. Por lo que, no debe de costar trabajo el acostumbrarse y explotar los beneficios de este increible compilador.

## Requisitos e instalaciones

Para poder adentrarse al entorno de Popurrí, es necesario hacer lo siguiente:

- [X] Tener instalado Python 3 o superior
- [X] Tener instalado Antlr 4.8 
- [X] Tener las bibliotecas externas instaladas

## Informacion importante

Popurrí es un lenguaje capaz pero no perfecto. Existen algunas caracteristicas que pueden llegar a ser diferentes de otros lenguajes. Estas son las siguientes:

Tipos de datos utilizados:
- INT
- FLOAT
- BOOL
- STRING

Tipos de acceso utilizados:
- PUBLIC
- PRIVATE
- PROTECTED

Por otro lado, Popurrí es un lenguaje en donde existe el orden. Lo anterior se refiere a que todas las declaraciones tienen un orden. Por lo que, no se puede declarar una clase despues de una funcion global, pero si al reves. Es decir, Popurrí trabaja de la siguiente manera:

Declaraciones en orden:
- Clases
- Variables
- Funciones

Despues de lo anterior, ahora si se puede realizar cualquier estatuo. Lo anterior trabaja como una funcion main.

Ahora bien, pasemos a la sintaxis de este lenguaje.


## Clases

Popurrí tiene la siguiente sintaxis para las clases

```
class numeros {
    private var numero : int
    func sumar(int numero_2) {
        numero += 1
    }
    var decimal : float
    protected var mensaje : string
}
```
Lo importante del codigo anterior es la sintaxis que se debe de utilizar para poder desarrollar una clase.

Se pueden utilizar los tipos de acceso para definir el alcance de un atributo o metodo. Si el tipo de acceso no esta explicito, el compilador asumira que este es un tipo de acceso `public`

Ahora, es una imitacion de un lenguaje orientado a objetos ¿Donde esta la herencia?

```
class numeros -> numeros_2 {
}
```

La herencia se maneja pasando primero el id de la clase padre, seguido de la clase hijo. Ademas, al igual que en otros lenguajes, los atributos de la clase padre se pasan directamente a la clase hijo.

## Funciones

La sintaxis de una funcion es la que sigue:

```
func a(int a, int b) int {
    a = 10
    return a + b
}
```

En el codigo anterior tenemos el tipo de retorno a la derecha del encabezado, esto nos parecio mas comodo en cuanto legibilidad. Por otro lado, se admiten parametros y retornos con expresiones, tal como se haria en un lenguaje moderno.

Por otra parte, las llamadas no difieren en lo absoluto de las que se acostumbran en otros lenguajes. Nuestra sintaxis para una llamada es la siguiente:

```
a(1,2)
```

Por ultimo, Popurrí maneja funciones especiales que nos ayudan a darle un enfoque mas profesional. Estas son las siguientes:

- input()
- print()
- println()

Por un lado, a `input` se le pasa una variable como parametro y al momento de la ejecucion del codigo, se activa y el usuario debe de escribir algo en consola para que se guarde el valor final en la variable.

Por otro lado, `print` y `println` son casi identicos. Mientras que `print` imprime datos utilizando un espacio como terminacion del buffer, println utiliza un `newline` como terminacion.

## Variables

