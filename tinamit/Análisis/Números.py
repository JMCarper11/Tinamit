import re


def tx_a_núm(texto):
    """
    Esta función toma texto de un número en cualquier idioma y lo cambia a un número Python.

    :param: El texto a convertir.
    :type texto: str

    :return: El número de Python correspondiendo
    :rtype: float

    """
    if texto[0] == '-':
        neg = -1
        texto = texto[1:]
    else:
        neg = 1

    if 'e' in texto.lower():
        texto, exp = texto.lower().split('e')
        exp = tx_a_núm(exp.strip('+'))
    else:
        exp = None

    for lengua, d_l in dic_trads.items():
        # Intentar cada lengua disponible.

        l_sep_dec = d_l['sep_dec']  # El separador de decimales
        if not isinstance(l_sep_dec, list):
            l_sep_dec = [l_sep_dec]

        l_núms = list(d_l['núms'])  # Los números

        # Ver si hay posibilidad de un sistema de bases
        try:
            bases = d_l['bases']
        except KeyError:
            bases = None

        # Intentar traducir literalmente, número por número
        for sep_dec in l_sep_dec:  # type: str
            try:
                núm = _trad_texto(texto=texto, núms=l_núms, sep_dec=sep_dec)
                # ¿Funcionó? ¡Perfecto!
                if exp is not None:
                    núm *= 10 ** exp
                return núm * neg if sep_dec in texto else int(núm) * neg
            except ValueError:
                pass  # ¿No funcionó? Qué pena. Ahora tenemos que trabajar.

        if bases is not None:
            # Intentar ver si puede ser un sistema de bases (unidades).

            sep_dec = None
            try:
                # Ver si hay de separar decimales
                entero = dec = None
                for sep_dec in l_sep_dec:
                    try:
                        entero, dec = texto.split(sep_dec)
                        break
                    except ValueError:
                        pass
                if entero is None:
                    entero = texto

                # Expresiones RegEx para esta lengua
                regex_núm = r'[{}]'.format(''.join([n for n in l_núms]))
                regex_unid = r'[{}]'.format(''.join([b[1] for b in bases]))
                regex = r'((?P<núm>{})?(?P<unid>{}|$))'.format(regex_núm, regex_unid)

                # Intentar encontrar secuencias de unidades y de números en el texto.
                m = re.finditer(regex, entero)
                resultados = [x for x in list(m) if len(x.group())]

                if not len(resultados):
                    # Si no encontramos nada, seguir con la próxima lengua
                    continue

                # Dividir en números y en unidades
                núms = [_trad_texto(g.group('núm'), núms=l_núms, sep_dec=sep_dec) if g.group('núm') is not None else 1
                        for g in resultados]
                unids = [_trad_texto(g.group('unid'), núms=[b[1] for b in bases], vals=[b[0] for b in bases],
                                     sep_dec=sep_dec)
                         if g.group('unid') is not None and len(g.group('unid')) else 1 for g in resultados]

                # Agregar o multiplicar valores, como necesario.
                val_entero = 0
                for í, (n, u) in enumerate(zip(núms, unids)):
                    if í == 0:
                        val_entero = n * u
                    else:
                        if u > unids[í - 1]:
                            val_entero = (val_entero + n) * u
                        else:
                            val_entero = val_entero + (n * u)
                val_entero = int(val_entero)

                # Calcular el número traducido
                if dec is not None:
                    # Si había decima, convertir el texto decimal
                    val_dec = _trad_texto(texto=dec, núms=l_núms, sep_dec=sep_dec, txt=True)

                    # Calcular el número
                    núm = float(str(val_entero) + sep_dec + val_dec)

                else:
                    # ... si no había decimal, no hay nada más que hacer
                    núm = val_entero

                if exp is not None:
                    núm *= 10 ** exp

                return núm * neg  # Devolver el número

            except (KeyError, ValueError):
                # Si no funcionó, intentemos otra lengua
                pass

    # Si ninguna de las lenguas funcionó, hubo error.
    raise ValueError('No se pudo decifrar el número %s' % texto)


def _trad_texto(texto, núms, sep_dec, vals=None, txt=False):
    """
    Esta función traduce un texto a un valor numérico o de texto (formato latino).

    :param texto: El texto para traducir.
    :type texto: str
    :param núms: La lista, en orden ascendente, de los carácteres que corresponden a los números 0, 1, 2, ... 9.
    :type núms: list[str]
    :param sep_dec: El separador de decimales
    :type sep_dec: str
    :param txt: Si hay que devolver en formato de texto
    :type txt: bool
    :return: El número convertido.
    :rtype: float | txt
    """

    if vals is None:
        vals = range(len(núms))

    if all([x in núms + [sep_dec] for x in texto]):
        # Si todos los carácteres en el texto están reconocidos...

        # Cambiar el separador de decimal a un punto.
        texto = texto.replace(sep_dec, '.')

        for v, n in zip(vals, núms):
            # Reemplazar todos los números también.
            texto = texto.replace(n, str(v))

        # Devolver el resultado, o en texto, o en formato numeral.
        if txt:
            return texto
        else:
            return float(texto)

    else:
        # Si no se reconocieron todos los carácteres, no podemos hacer nada más.
        raise ValueError('Texto "{}" no reconocido.'.format(texto))


dic_trads = {'Latino': {'núms': ('0', '1', '2', '3', '4', '5', '6', '7', '8', '9'),
                        'sep_dec': ['.', ',']},
             'हिंदी': {'núms': ('०', '१', '२', '३', '४', '५', '६', '७', '८', '९'),
                       'sep_dec': ['.', ',']},
             'ਪੰਜਾਬੀ': {'núms': ('੦', '੧', '੨', '੩', '੪', '੫', '੬', '੭', '੮', '੯'),
                        'sep_dec': ['.', ',']},
             'ગુજરાતી': {'núms': ('૦', '૧', '૨', '૩', '૪', '૫', '૬', '૭', '૮', '૯'),
                         'sep_dec': ['.', ',']},
             'മലയാളം': {'núms': ('൦', '൧', '൨', '൩', '൪', '൫', '൬', '൭', '൮', '൯'),
                        'sep_dec': ['.', ',']},
             'தமிழ்': {'núms': ('൦', '௧', '௨', '௩', '௪', '௫', '௬', '௭', '௮', '௯'),
                       'sep_dec': ['.', ','],
                       'bases': [(10, '௰'), (100, '௱'), (1000, '௲')]},
             'اردو': {'núms': ('٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩'),
                      'sep_dec': ['.', ',']},
             'العربية': {'núms': ('٠', '١', '٢', '٣', '٤', '٥', '٦', '٧', '٨', '٩',),
                         'sep_dec': ['.', ',']},
             'فارسی': {'núms': ('۰', '۱', '۲', '۳', '۴', '۵', '۶', '۷', '۸', '۹'),
                       'sep_dec': ['.', ',']},
             'ଓରିୟା': {'núms': ('୦', '୧', '୨', '୩', '୪', '୫', '୬', '୭', '୮', '୯'),
                       'sep_dec': ['.', ',']},
             'ಕನ್ನಡ': {'núms': ('೦', '೧', '೨', '೩', '೪', '೫', '೬', '೭', '೮', '೯'),
                       'sep_dec': ['.', ',']},
             'తెలుగు': {'núms': ('౦', '౧', '౨', '౩', '౪', '౫', '౬', '౭', '౮', '౯'),
                        'sep_dec': ['.', ',']},
             '汉语': {'núms': ('〇', '一', '二', '三', '四', '五', '六', '七', '八', '九'),
                    'sep_dec': ['.', ','],
                    'bases': [(10, '十'), (100, '百'), (1000, '千'), (10000, '万')]},
             '日本語': {'núms': ('〇', '一', '二', '三', '四', '五', '六', '七', '八', '九'),
                     'sep_dec': ['.', ','],
                     'bases': [(10, '十'), (100, '百'), (1000, '千'), (10000, '万')]},
             }
