import math as mat

import numpy as np
import regex
from lark import Lark, Transformer
from pkg_resources import resource_filename

from tinamit import _

try:
    import pymc3 as pm
except ImportError:
    pm = None

l_dialectos_potenciales = {
    'vensim': resource_filename('tinamit.Análisis', 'grams/gram_Vensim.g'),
    'tinamït': resource_filename('tinamit.Análisis', 'grams/gram_Vensim.g')  # Por el momento, es lo mismo
}
l_grams_def_var = {}
l_grams_var = {}


class _Transformador(Transformer):
    """
    Transformador de árboles sintácticos Lark a diccionarios Python.
    """

    @staticmethod
    def num(x):
        return float(x[0])

    @staticmethod
    def neg(x):
        return {'neg': x[0]}

    @staticmethod
    def var(x):
        return {'var': x[0]}

    @staticmethod
    def nombre(x):
        return str(x[0])

    @staticmethod
    def cadena(x):
        return str(x[0])

    @staticmethod
    def func(x):
        return {'func': x}

    @staticmethod
    def pod(x):
        return {'func': ['^', x]}

    @staticmethod
    def mul(x):
        return {'func': ['*', x]}

    @staticmethod
    def div(x):
        return {'func': ['/', x]}

    @staticmethod
    def suma(x):
        return {'func': ['+', x]}

    @staticmethod
    def sub(x):
        return {'func': ['-', x]}

    @staticmethod
    def asign_var(x):
        return {'var': x[0]['var'], 'ec': x[1]}

    @staticmethod
    def asign_sub(x):
        return {'sub': x[0]['var'], 'nmbr_dims': x[1]}

    args = list
    ec = list


class Ecuación(object):
    def __init__(símismo, ec, otras_ecs=None, nombres_equiv=None, nombre=None, dialecto=None):

        if otras_ecs is None:
            otras_ecs = {}

        if nombres_equiv is None:
            nombres_equiv = {}

        if dialecto is None:
            dialecto = 'tinamït'
        símismo.dialecto = dialecto

        símismo.nombre = nombre
        símismo.tipo = 'var'
        símismo.árbol = None

        if dialecto not in l_grams_var:
            with open(l_dialectos_potenciales[dialecto], encoding='UTF-8') as d:
                l_grams_var[dialecto] = Lark(d, parser='lalr', start='ec')
        anlzdr = l_grams_var[dialecto]

        árbol = _Transformador().transform(anlzdr.parse(ec))

        _subst_var_en_árbol(á=árbol, mp={v_otr: Ecuación(ec_otr).árbol for v_otr, ec_otr in otras_ecs.items()})

        _subst_var_en_árbol(á=árbol, mp=nombres_equiv)

        if isinstance(árbol, dict):
            try:
                símismo.nombre = árbol['var']
                símismo.árbol = árbol['ec']
            except KeyError:
                símismo.nombre = árbol['sub']
                símismo.árbol = árbol['nmbr_dims']
                símismo.tipo = 'sub'
        else:
            símismo.árbol = árbol[0]

    def variables(símismo):

        def _obt_vars(á):
            if isinstance(á, dict):

                for ll, v in á.items():

                    if ll == 'func':
                        if v[0] in ['+', '-', '/', '*', '^']:
                            vrs = _obt_vars(v[1][0])
                            vrs.update(_obt_vars(v[1][1]))

                            return vrs

                        else:
                            return set([i for x in v[1] for i in _obt_vars(x)])

                    elif ll == 'var':
                        return {v}

                    elif ll == 'neg':
                        return set()

                    else:
                        raise TypeError('')

            elif isinstance(á, list):
                return {z for x in á for z in _obt_vars(x)}
            elif isinstance(á, int) or isinstance(á, float):
                return set()
            else:
                raise TypeError('{}'.format(type(á)))

        return _obt_vars(símismo.árbol)

    def gen_func_python(símismo, paráms, otras_ecs=None):

        if otras_ecs is None:
            otras_ecs = {}

        dialecto = símismo.dialecto

        def _a_python(á, l_prms=paráms):

            if isinstance(á, dict):

                for ll, v in á.items():

                    if ll == 'func':

                        try:
                            op = _conv_op(v[0], dialecto, 'tinamït')

                            comp_1 = _a_python(v[1][0], l_prms=l_prms)
                            comp_2 = _a_python(v[1][1], l_prms=l_prms)

                            if op == '+':
                                return lambda p, vr: comp_1(p=p, vr=vr) + comp_2(p=p, vr=vr)
                            elif op == '/':
                                return lambda p, vr: comp_1(p=p, vr=vr) / comp_2(p=p, vr=vr)
                            elif op == '-':
                                return lambda p, vr: comp_1(p=p, vr=vr) - comp_2(p=p, vr=vr)
                            elif op == '*':
                                return lambda p, vr: comp_1(p=p, vr=vr) * comp_2(p=p, vr=vr)
                            elif op == '^':
                                return lambda p, vr: comp_1(p=p, vr=vr) ** comp_2(p=p, vr=vr)
                            elif op == '>':
                                return lambda p, vr: comp_1(p=p, vr=vr) > comp_2(p=p, vr=vr)
                            elif op == '<':
                                return lambda p, vr: comp_1(p=p, vr=vr) < comp_2(p=p, vr=vr)
                            elif op == '>=':
                                return lambda p, vr: comp_1(p=p, vr=vr) >= comp_2(p=p, vr=vr)
                            elif op == '<=':
                                return lambda p, vr: comp_1(p=p, vr=vr) <= comp_2(p=p, vr=vr)
                            elif op == '==':
                                return lambda p, vr: comp_1(p=p, vr=vr) == comp_2(p=p, vr=vr)
                            elif op == '!=':
                                return lambda p, vr: comp_1(p=p, vr=vr) != comp_2(p=p, vr=vr)
                            else:
                                raise ValueError(v[0])

                        except KeyError:
                            fun = _conv_fun(v[0], dialecto, 'python')
                            comp = _a_python(v[1][1], l_prms=l_prms)

                            return lambda p, vr: fun(*comp(p=p, vr=vr))

                    elif ll == 'var':
                        try:
                            í_var = l_prms.index(v)

                            return lambda p, vr: p[í_var]

                        except ValueError:
                            # Si el variable no es un parámetro calibrable, debe ser un valor observado, al menos
                            # que esté espeficado por otra ecuación.
                            if v in otras_ecs:

                                ec = otras_ecs[v]
                                if isinstance(ec, Ecuación):
                                    árb = ec.árbol
                                else:
                                    árb = Ecuación(ec).árbol
                                return _a_python(á=árb, l_prms=l_prms)

                            else:
                                return lambda p, vr: vr[v]

                    elif ll == 'neg':
                        comp = _a_python(v[1][1], l_prms=l_prms)
                        return lambda p, vr: -comp(p=p, vr=vr)
                    else:
                        raise TypeError('')

            elif isinstance(á, list):
                return [_a_python(x) for x in á]
            elif isinstance(á, int) or isinstance(á, float):
                return lambda p, vr: á
            else:
                raise TypeError('{}'.format(type(á)))

        return _a_python(símismo.árbol)

    def gen_mod_bayes(símismo, líms_paráms, obs_x, obs_y, aprioris=None, binario=False):

        if pm is None:
            return ImportError(_('Hay que instalar PyMC3 para poder utilizar modelos bayesianos.'))

        if obs_x is None:
            obs_x = {}
        if obs_y is None:
            obs_y = {}

        dialecto = símismo.dialecto

        def _gen_d_vars_pm():
            egr = {}
            for p, líms in líms_paráms.items():

                if aprioris is None:
                    if líms[0] is None:
                        if líms[1] is None:
                            dist_pm = pm.Flat(p, testval=0)
                        else:
                            dist_pm = líms[1] - pm.HalfFlat(p, testval=1)
                    else:
                        if líms[1] is None:
                            dist_pm = líms[0] + pm.HalfFlat(p, testval=1)
                        else:
                            dist_pm = pm.Uniform(name=p, lower=líms[0], upper=líms[1])
                else:
                    dist, prms = aprioris[p]
                    if (líms[0] is not None or líms[1] is not None) and dist != pm.Uniform:
                        acotada = pm.Bound(dist, lower=líms[0], upper=líms[1])
                        dist_pm = acotada(p, **prms)
                    else:
                        if dist == pm.Uniform:
                            prms['lower'] = max(prms['lower'], líms[0])
                            prms['upper'] = min(prms['upper'], líms[1])
                        dist_pm = dist(p, **prms)

                egr[p] = dist_pm
            return egr

        def _gen_d_vars_pm_jer():
            egr = {}

            for p, líms in líms_paráms.items():
                for nv in niveles:
                    pass

            return egr

        def _a_bayes(á, d_pm):

            if isinstance(á, dict):

                for ll, v in á.items():

                    if ll == 'func':

                        try:
                            op_pm = _conv_op(v[0], dialecto, 'pm')
                            return op_pm(_a_bayes(v[1][0], d_pm=d_pm), _a_bayes(v[1][1], d_pm=d_pm))
                        except KeyError:
                            pass

                        if v[0] == '+':
                            return _a_bayes(v[1][0], d_pm=d_pm) + _a_bayes(v[1][1], d_pm=d_pm)
                        elif v[0] == '/':
                            return _a_bayes(v[1][0], d_pm=d_pm) / _a_bayes(v[1][1], d_pm=d_pm)
                        elif v[0] == '-':
                            return _a_bayes(v[1][0], d_pm=d_pm) - _a_bayes(v[1][1], d_pm=d_pm)
                        elif v[0] == '*':
                            return _a_bayes(v[1][0], d_pm=d_pm) * _a_bayes(v[1][1], d_pm=d_pm)
                        elif v[0] == '^':
                            return _a_bayes(v[1][0], d_pm=d_pm) ** _a_bayes(v[1][1], d_pm=d_pm)

                        else:
                            return _conv_fun(v[0], dialecto, 'pm')(*_a_bayes(v[1], d_pm=d_pm))

                    elif ll == 'var':
                        try:
                            return d_pm[v]

                        except KeyError:

                            # Si el variable no es un parámetro calibrable, debe ser un valor observado
                            try:
                                return obs_x[v]
                            except KeyError:
                                raise ValueError(_('El variable "{}" no es un parámetro, y no se encuentra'
                                                   'en la base de datos observados tampoco.').format(v))
                    elif ll == 'neg':
                        return -_a_bayes(v, d_pm=d_pm)
                    else:
                        raise ValueError(_('Llave "{ll}" desconocida en el árbol sintático de la ecuación "{ec}". '
                                           'Éste es un error de programación en Tinamït.').format(ll=ll, ec=símismo))

            elif isinstance(á, list):
                return [_a_bayes(x, d_pm=d_pm) for x in á]
            elif isinstance(á, int) or isinstance(á, float):
                return á
            else:
                raise TypeError('')

        modelo = pm.Model()
        with modelo:
            d_vars_pm = _gen_d_vars_pm()
            mu = _a_bayes(símismo.árbol, d_vars_pm)
            sigma = pm.HalfNormal(name='sigma', sd=max(obs_y.abs()))

            if binario:
                x = pm.Normal(name='logit_prob', mu=mu, sd=sigma, shape=obs_y.shape, testval=np.full(obs_y.shape, 0))
                pm.Bernoulli(name='Y_obs', logit_p=-x, observed=obs_y)  #

            else:
                pm.Normal(name='Y_obs', mu=mu, sd=sigma, observed=obs_y)

        return modelo

    def sacar_args_func(símismo, func, i):

        árbol_ec_a_texto = símismo._árb_a_txt
        dialecto = símismo.dialecto

        def _buscar_func(á, f):

            if isinstance(á, dict):
                for ll, v in á.items():
                    if ll == 'func':
                        if v[0] == f:
                            return [árbol_ec_a_texto(x, dialecto=dialecto) for x in v[1][:i]]
                    else:
                        for p in v[1]:
                            _buscar_func(p, f=func)

            elif isinstance(á, list):
                [_buscar_func(x, f=func) for x in á]
            else:
                pass

        return _buscar_func(símismo.árbol, f=func)

    def __str__(símismo):
        return _árb_a_txt(símismo.árbol, símismo.dialecto)


# Funciones auxiliares para ecuaciones.
def _subst_var_en_árbol(á, mp):
    """
    Substituye variables en un árbol sintáctico. Funciona de manera recursiva.

    Parameters
    ----------
    á: dict
        El árbol sintáctico.
    mp: dict
        Un diccionario con nombres de variables y sus substituciones.

    """

    # Recursar a través del árbol.
    if isinstance(á, dict):
        # Si es diccionario, visitar todas sus ramas (llaves)

        for ll, v in á.items():

            if ll == 'func':
                # Para funciones, simplemente recursar a través de todos sus argumentos.
                for x in v[1]:
                    _subst_var_en_árbol(x, mp=mp)

            elif ll == 'var':
                # Para variables, subsituir si necesario.
                if v in mp:
                    á[ll] = mp[v]

            elif ll == 'neg' or ll == 'ec':
                # Para negativos y ecuaciones, seguir adelante
                _subst_var_en_árbol(v, mp=mp)

            else:
                # Dar error si encontramos algo que no reconocimos.
                raise TypeError(_('Componente de ecuación "{}" no reconocido.').format(ll))

    elif isinstance(á, list):
        # Para listas, recursar a través de cada elemento
        for x in á:
            _subst_var_en_árbol(x, mp=mp)

    elif isinstance(á, int) or isinstance(á, float):
        pass  # No hay nada que hacer para números.

    else:
        # El caso muy improbable de un error.
        raise TypeError(_('Componente de ecuación "{}" no reconocido.').format(type(á)))


def _árb_a_txt(árb, dialecto):
    """
    Convierte un árbol sintáctico de ecuación a formato texto. Funciona como función recursiva.

    Parameters
    ----------
    árb: dict
        El árbol sintáctico
    dialecto: str
        El dialecto del árbol.

    Returns
    -------
    str:
        La ecuación en formato texto.

    """

    # Simplificar el código
    dl = dialecto

    # Pasar a través todas las posibilidades para el árbol y sus ramas
    if isinstance(árb, dict):
        # Si es diccionario, pasar a través de todas sus ramas (llaves)
        for ll, v in árb.items():
            if ll == 'func':
                # Si es función, intentar tratarlo como operador primero
                try:
                    # Intentar convertir a dialecto Tinamït
                    tx_op = _conv_op(v[0], dialecto, 'tinamït')

                    # Devolver el texto correspondiendo a un operado (y recursar a través de los dos argumentos).
                    return '({a1} {o} {a2})'.format(a1=_árb_a_txt(v[1][0], dl), o=tx_op, a2=_árb_a_txt(v[1][1], dl))
                except KeyError:
                    pass  # Si no funcionó, tal vez no es operador.

                try:
                    # Intentar convertirlo, como nombre de función, a dialecto Tïnamit
                    return '{nombre}({args})'.format(nombre=_conv_fun(v[0], dialecto, 'tinamït'),
                                                     args=_árb_a_txt(v[1], dl))
                except KeyError:
                    # Si no funcionó, simplemente formatearlo con el nombre original de la función.
                    return '{nombre}({args})'.format(nombre=v[0], args=_árb_a_txt(v[1], dl))

            elif ll == 'var':
                # Si es variable, simplemente devolver el nombre del variable
                return v

            elif ll == 'neg':
                # Formatear negativos
                return '-{}'.format(_árb_a_txt(v, dl))

            else:
                # Si no es función, variable o negativo, tenemos error.
                raise TypeError(_('Componente "{}" del árbol no reconocido.'))

    elif isinstance(árb, list):
        # Si es lista (por ejemplo, un lista de parámetros de una ecuación), recursar a través de sus elementos.
        return ', '.join([_árb_a_txt(x, dl) for x in árb])

    elif isinstance(árb, int) or isinstance(árb, float):
        # Números se devuelven así
        return str(árb)

    else:
        # Si no es diccionario, lista, o número, no sé lo que es.
        raise TypeError(_('Tipo de componente "{}" no reconocido en el árbol sintáctico.').format(type(árb)))


# Un diccionario con conversiones de funciones reconocidas. Si quieres activar más funciones, agregarlas aqui.
_dic_funs = {
    'mín': {'vensim': 'MIN', 'pm': pm.math.minimum if pm is not None else None, 'python': min},
    'máx': {'vensim': 'MAX', 'pm': pm.math.maximum if pm is not None else None, 'python': max},
    'abs': {'vensim': 'ABS', 'pm': pm.math.abs_ if pm is not None else None, 'python': abs},
    'exp': {'vensim': 'EXP', 'pm': pm.math.exp if pm is not None else None, 'python': mat.exp},
    'ent': {'vensim': 'INTEGER', 'pm': pm.math.floor if pm is not None else None, 'python': int},
    'rcd': {'vensim': 'SQRT', 'pm': pm.math.sqrt if pm is not None else None, 'python': mat.sqrt},
    'ln': {'vensim': 'LN', 'pm': pm.math.log if pm is not None else None, 'python': mat.log},
    'log': {'vensim': 'LOG', 'pm': None if pm is None else lambda x: pm.math.log(x) / mat.log(10), 'python': mat.log10},
    'sin': {'vensim': 'SIN', 'pm': pm.math.sin if pm is not None else None, 'python': mat.sin},
    'cos': {'vensim': 'COS', 'pm': pm.math.cos if pm is not None else None, 'python': mat.cos},
    'tan': {'vensim': 'TAN', 'pm': pm.math.tan if pm is not None else None, 'python': mat.tan},
    'sinh': {'vensim': 'SINH', 'pm': pm.math.sinh if pm is not None else None, 'python': mat.sinh},
    'cosh': {'vensim': 'COSH', 'pm': pm.math.cosh if pm is not None else None, 'python': mat.cosh},
    'tanh': {'vensim': 'TANH', 'pm': pm.math.tanh if pm is not None else None, 'python': mat.tanh},
    'asin': {'vensim': 'ARCSIN', 'python': mat.asin},
    'acos': {'vensim': 'ARCCOS', 'python': mat.acos},
    'atan': {'vensim': 'ARCTAN', 'python': mat.atan},
    'si_sino': {'vensim': 'IF THEN ELSE', 'pm': pm.math.switch if pm is not None else None,
                'python': lambda cond, si, sino: si if cond else sino}
}

# Diccionario de operadores. Notar que algunos se traducen por funciones en PyMC3.
_dic_ops = {
    '>': {'vensim': '>', 'pm': pm.math.gt if pm is not None else None},
    '<': {'vensim': '<', 'pm': pm.math.lt if pm is not None else None},
    '>=': {'vensim': '>=', 'pm': pm.math.ge if pm is not None else None},
    '<=': {'vensim': '<=', 'pm': pm.math.le if pm is not None else None},
    '==': {'vensim': '=', 'pm': pm.math.eq if pm is not None else None},
    '!=': {'vensim': '<>', 'pm': pm.math.neq if pm is not None else None},
    '+': {'vensim': '+'},
    '-': {'vensim': '-'},
    '*': {'vensim': '*'},
    '^': {'vensim': '^'},
    '/': {'vensim': '/'}
}


# Funciones auxiliares
def _conv_fun(fun, dialecto_orig, dialecto_final):
    """
    Traduce una función a otro dialecto.

    Parameters
    ----------
    fun: str
        La función para traducir.
    dialecto_orig: str
        El dialecto original de la función.
    dialecto_final: str
        El dialecto final deseado.

    Returns
    -------
    str
        La función traducida.
    """

    if dialecto_final == dialecto_orig:
        return fun
    if dialecto_orig == 'tinamït':
        return _dic_funs[fun][dialecto_final]
    else:
        if dialecto_final == 'tinamït':
            return next(ll for ll, d in _dic_funs.items() if d[dialecto_orig] == fun)
        else:
            return next(d[dialecto_final] for ll, d in _dic_funs.items() if d[dialecto_orig] == fun)


def _conv_op(oper, dialecto_orig, dialecto_final):
    """
    Traduce un operador a otro dialecto.

    Parameters
    ----------
    oper: str
        El operador para traducir.
    dialecto_orig: str
        El dialecto original del operador.
    dialecto_final: str
        El dialecto final deseado.

    Returns
    -------
    str
        El operador traducido.
    """

    if dialecto_final == dialecto_orig:
        return oper
    if dialecto_orig == 'tinamït':
        return _dic_ops[oper][dialecto_final]
    else:
        if dialecto_final == 'tinamït':
            return next(ll for ll, d in _dic_ops.items() if d[dialecto_orig] == oper)
        else:
            return next(d[dialecto_final] for ll, d in _dic_ops.items() if d[dialecto_orig] == oper)


# Para hacer: Funciones que hay que reemplazar con algo más elegante
def juntar_líns(l, cabeza=None, cola=None):
    """
    Esta función junta una lista de líneas de texto en una sola línea de texto.

    :param l: La lexta de líneas de texto.
    :type l: list[str]

    :param cabeza:
    :type cabeza:

    :param cola:
    :type cola:

    :return: El texto combinado.
    :rtype: str

    """

    # Quitar text no deseado del principio y del final
    if cabeza is not None:
        l[0] = regex.sub(r'^({})'.format(cabeza), '', l[0])
    if cola is not None:
        l[-1] = regex.sub(r'{}$'.format(cola), '', l[-1])

    # Quitar tabulaciones y símbolos de final de línea
    l = [x.lstrip('\t').rstrip('\n').rstrip('\\') for x in l]

    # Combinar las líneas y quitar espacios al principio y al final
    texto = ''.join(l).strip(' ')

    # Devolver el texto combinado.
    return texto
