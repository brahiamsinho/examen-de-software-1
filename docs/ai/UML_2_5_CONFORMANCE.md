# Conformidad de Modelia con UML 2.5

Documento para la defensa. Compara lo que implementa Modelia con la norma **OMG UML 2.5.1**
(formal/17-12-05, diciembre de 2017). Cada fila de la matriz se verificó en el código; la columna «Dónde» dice en cuál.

## Veredicto

**Modelia no cumple UML 2.5 completo.** Implementa un **subconjunto del diagrama de clases**: clases, atributos,
operaciones, enumeraciones y cuatro tipos de relación, con reglas de validación propias. Hace **solo diagramas
de clases** (UML 2.5 define 14 tipos de diagrama) y exporta a **XMI 1.1 / UML 1.3**, no a XMI 2.5.1.

Frase para la defensa:
> «Implementamos un subconjunto del diagrama de clases de UML 2.5, con las restricciones de buena formación que ese
> subconjunto necesita, y lo exportamos a XMI. No cubrimos el lenguaje completo; lo que falta está listado y priorizado.»

## Cómo se sabe si cumple (método)

1. **Fuente de verdad.** La norma: https://www.omg.org/spec/UML/2.5.1 (PDF `formal/17-12-05`). Para máquinas, el
   metamodelo oficial: https://www.omg.org/spec/UML/20161101/UML.xmi y los tipos primitivos en `PrimitiveTypes.xmi`.
2. **Un producto cumple «por partes».** La norma distingue cumplir la sintaxis abstracta (qué elementos existen), la
   concreta (cómo se dibujan) y el intercambio de modelos (XMI). Se declara cuáles se cumplen (verifica la redacción
   exacta en la cláusula de conformidad del PDF: no pude abrirlo desde aquí).
3. **Se compara elemento por elemento** (la matriz de abajo) y se prueba el intercambio abriendo un archivo exportado
   en otra herramienta (Enterprise Architect, StarUML, Papyrus).

## Matriz: diagrama de clases de UML 2.5 frente a Modelia

Leyenda: ✅ cumple · ◐ parcial · ❌ no está. «Dónde» = archivos bajo `backend/apps/`.

### Clasificadores y propiedades

| Elemento UML 2.5 | Modelia | Dónde | Nota |
|---|---|---|---|
| Class (nombre, visibilidad) | ✅ | `uml_modeling/domain/elements.py` `UmlClass` | |
| Visibilidad public / private / protected / package | ✅ | `elements.py` `Visibility` | Las cuatro de `VisibilityKind` |
| Property (atributo): nombre, tipo, visibilidad | ◐ | `elements.py` `UmlAttribute` | Sin multiplicidad, valor por defecto, `static`, `readOnly`, derivado |
| Operation: nombre, parámetros, tipo de retorno, visibilidad | ◐ | `elements.py` `UmlOperation`, `UmlParameter` | Sin dirección de parámetro (in/out), `static`, `abstract` |
| Class abstracta (`isAbstract`) | ❌ | — | No existe el campo |
| Interface e InterfaceRealization | ❌ | — | |
| Enumeration y EnumerationLiteral | ✅ | `elements.py` `Enumeration` | `value` en el literal es una extensión, no de UML |
| DataType definido por el usuario | ❌ | — | |
| PrimitiveType | ◐ | `elements.py` `PrimitiveType` | Conjunto cerrado de 8 (String, Text, Integer, Long, Decimal, Boolean, Date, DateTime). UML define Boolean, Integer, Real, String, UnlimitedNatural |

### Relaciones

| Elemento UML 2.5 | Modelia | Dónde | Nota |
|---|---|---|---|
| Association binaria con nombre | ✅ | `elements.py` `Relationship` | |
| Extremos con multiplicidad y rol | ✅ | `RelationshipEnd`, `Multiplicity` | `null` en el límite superior = `*` |
| Aggregation (compartida) | ✅ | `RelationshipKind.AGGREGATION` | |
| Composition | ✅ | `RelationshipKind.COMPOSITION` | |
| Generalization | ✅ | `RelationshipKind.GENERALIZATION` | `source` = hija, `target` = padre |
| Navegabilidad de un extremo | ❌ | — | |
| Asociación n-aria, AssociationClass | ❌ | — | |
| Dependency, Usage, Realization | ❌ | — | |

### Estructura y otros elementos

| Elemento UML 2.5 | Modelia | Nota |
|---|---|---|
| Package | ❌ | El modelo es plano; el XMI exportado lo envuelve en un único paquete |
| Estereotipos y perfiles | ❌ | El «perfil de generación» de Modelia es un concepto propio, no un UML Profile |
| Comentarios / notas, restricciones (OCL) | ❌ | |
| Plantillas (clases parametrizadas) | ❌ | |
| Otros diagramas (casos de uso, secuencia, estados, actividades, componentes…) | ❌ | Solo diagrama de clases |

### Reglas de buena formación (validación)

Código: `uml_modeling/validation/rules/`. Las reglas de abajo coinciden con restricciones de la norma
(se ven en las cláusulas de Classifier, Namespace y MultiplicityElement).

| Regla de Modelia | Gravedad | ¿Corresponde a UML? |
|---|---|---|
| `GENERALIZATION_CYCLE` | error | ✅ UML prohíbe ciclos de generalización |
| `DUPLICATE_*` (clase, atributo, operación, literal) | error | ✅ Nombres distinguibles dentro de su espacio |
| `INVALID_MULTIPLICITY` | error | ✅ Límite inferior ≥ 0 y superior ≥ inferior |
| `EMPTY_ELEMENT_NAME` | error | ◐ UML permite elementos sin nombre; aquí no |
| `INVALID_RELATIONSHIP_ENDPOINT`, `UNKNOWN_ATTRIBUTE_TYPE` | error | ✅ Referencias a elementos que existen |
| `MULTI_PARENT_GENERALIZATION` | error | ❌ **UML permite herencia múltiple**; Modelia la prohíbe porque el mapeo relacional usa herencia de tabla única |
| `SELF_ASSOCIATION` | aviso | ❌ UML permite asociaciones reflexivas; aquí solo se avisa |
| `CLASS_WITHOUT_ATTRIBUTES` | aviso | ❌ UML permite clases sin atributos; es una ayuda al diseñador |

### Intercambio de modelos (XMI)

| Aspecto | Modelia | Norma UML 2.5.1 |
|---|---|---|
| Formato | XMI **1.1** | XMI **2.5.1** |
| Metamodelo | **UML 1.3** (`omg.org/UML1.3`), dialecto de Enterprise Architect | UML 2.5.1, espacio `http://www.omg.org/spec/UML/20161101` |
| Dónde | `xmi_interop/exporter.py` | |
| Diagrama | Guarda la posición de las clases | Diagram Interchange (UMLDI) |

Es el hueco más visible si el docente exige UML 2.5 de forma estricta: lo que se exporta es del estándar anterior.

## Lo que sí se puede afirmar

- Sintaxis abstracta: un subconjunto del diagrama de clases (tabla de arriba).
- Buena formación: las restricciones de ciclos, nombres, multiplicidad y referencias.
- Intercambio: XMI 1.1 / UML 1.3 (no XMI 2.5.1).
- Decisiones propias, documentadas: herencia simple y 8 tipos primitivos, por la generación de código y el mapeo relacional.

## Brechas, de mayor a menor valor por esfuerzo

1. **Clases abstractas, interfaces y realización.** Lo más visible en un diagrama de clases real. Toca el modelo, la
   validación, el lienzo y el generador.
2. **Dependencia.** Un tipo más de relación.
3. **Navegabilidad** y multiplicidad de atributos.
4. **Exportar XMI 2.5.1 / UML 2.5.1** y validarlo contra `UML.xmi`: es la única forma de afirmar conformidad de
   intercambio. Es el trabajo más grande de la lista.
5. Paquetes y estereotipos.

## Cómo repetir las comprobaciones

- Reglas de validación: `docker compose run --rm --entrypoint python backend -m pytest apps/uml_modeling`.
- Intercambio: crear un diagrama, exportarlo desde la app y abrir el XMI en Enterprise Architect o StarUML.
