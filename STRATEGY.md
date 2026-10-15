# STRATEGY.md — Estrategia a largo plazo de Estila

> Decisiones estructurales y su fundamento. Cambiar una estrategia requiere
> actualizar este archivo y el código afectado.

## 1. Aislamiento por capas (defensa en profundidad)

1. **App**: todo query operativo filtra `tenant_id`; token JWT debe coincidir
   con `X-Tenant-ID` (RNF02).
2. **BD**: VPD Oracle como red de seguridad ante bugs de la capa 1.
3. **Excepción diseñada**: el login no conoce el tenant → email único global +
   `auth_mode()` acotado (con `finally` + limpieza en `checkin` del pool).

## 2. Integridad antes que comodidad

- Estados de turno como máquina cerrada (nada sale de terminales) y motivo
  de cancelación obligatorio (mide ausentismo, objetivo del anteproyecto).
- Historial intocable: baja lógica en personal, borrado condicional en
  clientes/servicios (409 si hay referencias), eliminar-turno solo RESERVADO.
- `n_visitas` deriva de ATENDIDO real, no de reservas (métrica honesta para CRM).

## 3. Oracle primero, costo cero

- ADB Always Free: Postgres externo sobra; Oracle da VPD + respaldos sin pagar.
- SQLite solo dev; Postgres quedó legado. La app es mult dialecto pero el
  camino soportado es SQLite→Oracle (ver `DEPLOY_ORACLE.md`).
- Peculiaridades asumidas: `''→NULL`, `NUMBER→Decimal`, TZ naive al comparar.

## 4. Despliegue por etapas

- Dev en PC → pruebas en Vercel+ADB → producción en VM Oracle+ADB+Caddy.
- Vercel sirve para validar (serverless: frío, timeout 10 s, sin fondo);
  el sistema con estado vive en la VM. GitHub Pages no aplica (estático).
- HTTPS gratis con DuckDNS al inicio; dominio propio al salir a clientes
  (SIFEN y WhatsApp exigen presencia fiscal y URL pública serias).

## 5. Piloto antes que escala (RNF07/RNF09)

- Un tenant real (Arselia) validando agenda + caja antes del segundo tenant.
- Alta de tenant autoproporcionada (`POST /tenants` crea tenant+admin);
  facturación por suscripción cuando haya tracción, no antes.
- Umbral de diseño: 100 tenants concurrentes con RNF05 (1,5 s p95).

## 6. Cumplimiento y riesgo

- SIFEN multicontribuyente: cada tenant timbra con su RUC/timbrado/certificado
  custodiado cifrado (RNF04); sin docs fiscales reales sin confirmación.
- Datos personales (Paraguay): fichas con alergias son sensibles — mínimo
  acceso por rol (estilista solo su agenda) y nada en logs.
- Credenciales y wallets nunca en git; secretos solo por entorno.

## 7. Canal conversacional (reglas hoy, IA mañana)

- Una sola lógica de turnos/notificaciones, N canales: la demo web y el futuro
  WhatsApp comparten servicios; el adaptador solo traduce transporte.
- Reglas primero (costo cero, determinista, testeable sin red) para validar el
  flujo con Arselia; LLM después solo para entender lenguaje libre.
- Notificación como registro con ciclo de vida (PENDIENTE→ENVIADA/CANCELADA),
  nunca envíos silenciosos: en demo se marcan a mano, en real con acuse.
- Sesiones identificadas por cliente + historial persistido (trazabilidad ante
  reclamos: quién confirmó/canceló, cuándo y por qué motivo).
