# PLAN.md — Hoja de ruta de Estila

> Estado al 2026-10-14. Ver `STRATEGY.md` para el porqué y `HUMAN.md` para
> qué se necesita del humano en cada fase. RF/RNF = anteproyecto.

## Fase 0 — Base multitenant + web (hecha)

- [x] RF01/RF02: tenants + auth JWT con roles ADMIN/RECEPCION/ESTILISTA, RLS/VPD
- [x] RF03/RF10/RF12/RF05/RF06/RF09: CRUD personal/clientes/servicios/turnos,
  bloqueo de agenda, sin-turno, reprogramar, cancelar con motivo, atender (+visita)
- [x] Reglas: antisolape 409, email global unico, ultimo ADMIN, baja logica,
  borrado condicional, profesional inactivo sin turnos
- [x] Web con login por cookie y menu por rol + tema empresarial + `/docs` API
- [x] Migración a Oracle: driver, VPD (`adb_setup_admin.sql`, `vpd_oracle.sql`),
  `probar_oracle.py`, `DEPLOY_ORACLE.md`, `DEPLOY_VERCEL.md`
- [x] Soporte Vercel (Mangum) y repo GitHub público
- [x] Docs: AGENTS.md, HUMAN.md, PLAN.md, STRATEGY.md

## Fase 1 — Dinero (siguiente, en este orden)

- [ ] RF14 POS: ventas de servicios/productos multimedio (efectivo, transferencia, tarjeta, QR)
- [ ] RF16 Caja: apertura, egresos menores, arqueo ciego, cierre + diferencia
- [ ] RF13 Inventario/kárdex: entradas/salidas automáticas, punto de reposición
- [ ] RF17 Comisiones: cálculo por % de servicio + liquidación por período
- [ ] RF18 Reportes: ventas por período, servicios top, ocupación, PyG
- [ ] RF20 Auditoría: bitácora inmutable de operaciones sensibles

## Fase 2 — Integraciones (requieren decisiones y cuentas humanas)

- [ ] RF15 SIFEN: XML + firma XAdES por tenant, KuDE, eventos (nec. certificado Arselia)
- [ ] RF07/RF08 Agente IA WhatsApp: Cloud API + LLM provider-agnostic, recordatorios
- [ ] RF19 Vitrina e-commerce conectada al kárdex (entrega tercerizada)
- [ ] RF04 Configuración del tenant: horarios, feriados, puestos

## Fase 3 — Producción profesional

- [ ] `probar_oracle.py` en ADB real → Vercel pruebas → VM prod + Caddy + dominio
- [ ] Respaldos diarios verificados (RNF08) + monitoreo `/health` (RNF16)
- [ ] Alembic para migraciones (hoy `create_all` solo-dev)
- [ ] MFA para ADMIN (RNF03), endurecimiento, suite en CI

## Deuda conocida (no olvidar)

- `sql/rls.sql` es legado Postgres, sin mantenimiento (motor oficial: Oracle).
- `GET /tenants` abierto (falta rol superadmin).
- `JWT_SECRET`/`MASTER_KEY` de ejemplo solo para dev local.
- Modelos `venta/caja/comision/auditoria` sin routers (llegan en Fase 1).
- `estila.db` local con datos de prueba (no versionado, regenerable).
