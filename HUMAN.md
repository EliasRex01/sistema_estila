# HUMAN.md — Rol del humano en Estila

> El sistema se construye entre dos partes: el agente (código) y vos (contexto,
> accesos y decisiones). Idioma: español, respuestas cortas.

## 1. Lo que solo vos podés dar

| Tema | Detalle |
|---|---|
| Piloto Arselia | Datos reales del negocio, validación de que el flujo sirve en mostrador. Sin tu "esto así no se usa" no hay avance útil. |
| Decisiones | Pasar a Oracle/ADB, hacer público el repo, orden de módulos (POS vs SIFEN vs IA), borrar datos. El agente propone, vos disponés. |
| Cuentas nube | Consolas OCI (ADB, wallet, VM), Vercel (env vars, deploy), GitHub. El agente no entra a tus cuentas. |
| Verdad externa | Si SIFEN/WhatsApp/Marangatú cambió algo, tu captura o texto del portal vigente vale más que cualquier suposición. |
| Dinero real | Cobros, certificados digitales `.p12` y claves SIFEN, número de WhatsApp Business. Nada de esto se mueve sin tu confirmación explícita. |
| Teléfonos de clientes | Para el WhatsApp real cada ficha debe tener el número verdadero (hoy la demo acepta cualquier identificador). Si ves fichas demo ("Chat Demo", "Crud"), son filas de prueba. |

## 2. Cuentas y accesos

1. **GitHub**: repo `EliasRex01/sistema_estila` (público). "Publicá" = commit + push.
2. **Oracle Cloud**: tenant + usuario ADMIN de ADB para `adb_setup_admin.sql`, descarga del wallet a `wallet/` (nunca se commitea).
3. **Vercel**: importar el repo, cargar `ORACLE_*`, `JWT_SECRET` (32+), `MASTER_KEY`. Detalle en `DEPLOY_VERCEL.md`.
4. **(Futuro)** Meta Developers (WhatsApp Cloud) y DNIT (certificado por tenant, RUC/timbrado de Arselia).

## 3. Cómo pedir cosas (para que salgan en un intento)

- Una tarea por mensaje, con el resultado esperado ("al reservar solapado debe decir X").
- Si algo falla, pegá el mensaje exacto o la captura; no re-describas.
- "Corré el sistema" = levantar servidor en 8001 para ver en navegador. "Abrí X" incluye la URL + usuarios de prueba.
- Tus notas en archivos (ej. `DEPLOY_VERCEL.md`) **no se tocan sin tu permiso**: si algo ahí es riesgoso (ej. claves), se te avisa primero.

## 4. Lo que el agente hace sin preguntar

- Verificar con ejecución (tests, endpoints/páginas vivas, scripts `check_*`).
- Limpiar archivos de prueba y debug, no commitear secretos (`.env`, `*.db`, `.venv/`, `wallet/`).
- Documentar lo aprendido en `AGENTS.md`/`PLAN.md`/`STRATEGY.md`.
- Decirte cuando algo **no** se puede (ej. GitHub Pages no corre Python) en vez de simularlo.

## 5. Límites

- El agente no opera tus consolas (OCI, Vercel, Meta, DNIT) ni toca tus archivos de notas sin permiso.
- Sin documentos fiscales reales ni cobros sin tu confirmación explícita.
- La vía Oracle está completa en código pero verificada en vivo solo en SQLite hasta que `probar_oracle.py` dé `ALL ORACLE OK` contra tu ADB real.
- Los montos/comisiones de ejemplo se validan con Arselia antes de liquidar de verdad.
- La BD dev (`estila.db`) acumula filas de prueba con nombres claros; para
  partir de cero: borrar `estila.db` y correr `py -m app.db.init_db`.
