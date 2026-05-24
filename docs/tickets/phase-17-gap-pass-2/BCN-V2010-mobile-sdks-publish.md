# BCN-V2010 — SDK iOS Swift + Android Kotlin publish (BCN-066)

**Owner**: backend mobile
**Estimativa**: L (2 sprints)
**Pré-requisitos**: BCN-060..065 push mobile working
**Detected by**: audit pass-2 (2026-05-24, ainda em backlog BCN-066)

## Contexto

BCN-066 marked [ ]: SDK iOS (Swift) + Android (Kotlin) — separate repos.
Sem SDKs, clientes mobile precisam implementar APNs/FCM enrollment
manualmente → adoção lenta.

## Definição

1. Repo `rewire-labs/rewire-beacon-sdk-ios`:
   - SwiftPM package
   - `BeaconSDK.init(apiKey:)` + `BeaconSDK.registerDeviceToken()`
   - APNs registration UNUserNotificationCenter wiring
2. Repo `rewire-labs/rewire-beacon-sdk-android`:
   - Maven artifact `dev.rewirelabs:beacon-sdk:0.1.0`
   - `BeaconSDK.init(context, apiKey)` + auto-FCM enrollment
3. Sample apps iOS + Android em `examples/`.
4. CI publish para CocoaPods + Maven Central (rewire-labs publisher account).
5. Document em `docs/sdk/ios.md` + `docs/sdk/android.md`.

## Critérios de aceite

- [ ] SDKs publicados versão 0.1.0
- [ ] Sample apps build + push received roundtrip works
- [ ] Documentation 1-line bootstrap per platform
- [ ] CHANGELOG mantido per release

## Referências

- BCN-066 (original)
- BCN-060..065 stack existente
