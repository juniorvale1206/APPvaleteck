# Valeteck — Mobile MVP (PRD)

## Visão
App mobile (React Native / Expo) para técnicos da Valeteck registrarem atendimentos de instalação veicular em campo, com checklist guiado, evidências fotográficas, geolocalização, assinatura do cliente e validações antifraude mínimas.

## Stack
- Frontend: Expo SDK 54 + Expo Router + React Native
- Backend: FastAPI + Motor (MongoDB)
- Auth: JWT Bearer (custom email/senha)
- Storage: MongoDB; fotos e assinatura em base64

## Personas
- Técnico instalador (operador principal)
- Admin (auditoria futura)

## Funcionalidades MVP
1. Login com sessão persistente (AsyncStorage)
2. Home com lista de checklists, busca por placa/cliente, status colorido
3. Criação de checklist em 5 etapas:
   - Cliente (nome, sobrenome, placa Br, telefone, obs)
   - Instalação (empresa fixa, equipamento, tipo, acessórios multi)
   - Evidências (mínimo 2 fotos via câmera/galeria + GPS opcional)
   - Assinatura touch (limpar/confirmar) com nome para conferência
   - Revisão final + envio
4. Detalhes do checklist (com alertas antifraude)
5. Rascunho local + persistência no servidor
6. Logout

## Antifraude (MVP)
- Validações obrigatórias front+back
- Alerta de duplicidade (mesma placa enviada < 24h)
- Alerta de garantia (instalação anterior < 30d para mesma placa)

## Telas
splash, login, home, perfil, checklist/new (5 etapas), checklist/[id]

## Identidade Visual
Preto + amarelo Valeteck (#000 + #FFD400), tipografia clara, botões grandes (≥56px), foco em uso com uma mão.

## Não escopo
Painel web, financeiro, OCR, IA, push, offline robusto.
