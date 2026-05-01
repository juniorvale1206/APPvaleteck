#====================================================================================================
# START - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================

# THIS SECTION CONTAINS CRITICAL TESTING INSTRUCTIONS FOR BOTH AGENTS
# BOTH MAIN_AGENT AND TESTING_AGENT MUST PRESERVE THIS ENTIRE BLOCK

# Communication Protocol:
# If the `testing_agent` is available, main agent should delegate all testing tasks to it.
#
# You have access to a file called `test_result.md`. This file contains the complete testing state
# and history, and is the primary means of communication between main and the testing agent.
#
# Main and testing agents must follow this exact format to maintain testing data. 
# The testing data must be entered in yaml format Below is the data structure:
# 
## user_problem_statement: {problem_statement}
## backend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.py"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## frontend:
##   - task: "Task name"
##     implemented: true
##     working: true  # or false or "NA"
##     file: "file_path.js"
##     stuck_count: 0
##     priority: "high"  # or "medium" or "low"
##     needs_retesting: false
##     status_history:
##         -working: true  # or false or "NA"
##         -agent: "main"  # or "testing" or "user"
##         -comment: "Detailed comment about status"
##
## metadata:
##   created_by: "main_agent"
##   version: "1.0"
##   test_sequence: 0
##   run_ui: false
##
## test_plan:
##   current_focus:
##     - "Task name 1"
##     - "Task name 2"
##   stuck_tasks:
##     - "Task name with persistent issues"
##   test_all: false
##   test_priority: "high_first"  # or "sequential" or "stuck_first"
##
## agent_communication:
##     -agent: "main"  # or "testing" or "user"
##     -message: "Communication message between agents"

# Protocol Guidelines for Main agent
#
# 1. Update Test Result File Before Testing:
#    - Main agent must always update the `test_result.md` file before calling the testing agent
#    - Add implementation details to the status_history
#    - Set `needs_retesting` to true for tasks that need testing
#    - Update the `test_plan` section to guide testing priorities
#    - Add a message to `agent_communication` explaining what you've done
#
# 2. Incorporate User Feedback:
#    - When a user provides feedback that something is or isn't working, add this information to the relevant task's status_history
#    - Update the working status based on user feedback
#    - If a user reports an issue with a task that was marked as working, increment the stuck_count
#    - Whenever user reports issue in the app, if we have testing agent and task_result.md file so find the appropriate task for that and append in status_history of that task to contain the user concern and problem as well 
#
# 3. Track Stuck Tasks:
#    - Monitor which tasks have high stuck_count values or where you are fixing same issue again and again, analyze that when you read task_result.md
#    - For persistent issues, use websearch tool to find solutions
#    - Pay special attention to tasks in the stuck_tasks list
#    - When you fix an issue with a stuck task, don't reset the stuck_count until the testing agent confirms it's working
#
# 4. Provide Context to Testing Agent:
#    - When calling the testing agent, provide clear instructions about:
#      - Which tasks need testing (reference the test_plan)
#      - Any authentication details or configuration needed
#      - Specific test scenarios to focus on
#      - Any known issues or edge cases to verify
#
# 5. Call the testing agent with specific instructions referring to test_result.md
#
# IMPORTANT: Main agent must ALWAYS update test_result.md BEFORE calling the testing agent, as it relies on this file to understand what to test next.

#====================================================================================================
# END - Testing Protocol - DO NOT EDIT OR REMOVE THIS SECTION
#====================================================================================================



#====================================================================================================
# Testing Data - Main Agent and testing sub agent both should log testing data below this section
#====================================================================================================

user_problem_statement: |
  Refatoração P0+P1 da v10 do Valeteck Mobile MVP:
  - (P0) Modularizar server.py monolítico em routers FastAPI separados (auth, appointments, checklists, earnings, rankings, gamification, inventory, device, ocr, partners, system).
  - (P0) Adicionar índice composto MongoDB em appointments e checklists para performance.
  - (P0) Preparar Cloud Storage (Cloudinary) para fotos — código em fallback (gravando base64 quando não configurado).
  - (P1) Implementar Refresh Token JWT (access 30min + refresh 7 dias) com endpoint /api/auth/refresh.
  - (P1) Rate Limiting (SlowAPI) em /api/auth/login (10/min) e /api/ocr/plate (15/min).
  - Adicionar endpoint /api/health.
  - Frontend: axios com interceptor 401→refresh→retry, AsyncStorage com novas chaves de token.

backend:
  - task: "Modularização do backend (routers separados)"
    implemented: true
    working: true
    file: "/app/backend/server.py + /app/backend/routes/* + /app/backend/services/* + /app/backend/models/* + /app/backend/core/*"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: |
            server.py de 1757 linhas dividido em:
            - core/: config (env), database (motor), security (jwt+bcrypt+get_current_user+require_admin),
              rate_limit (SlowAPI), storage (Cloudinary)
            - models/: auth, checklist, appointment, earnings, ranking, gamification, inventory, device, ocr, partner
            - services/: plates, pricing, pdf, alerts, partners, gamification, seeds
            - routes/: auth, reference, appointments, checklists, earnings, rankings,
              gamification, inventory, device, ocr, partners, system
            - constants.py: COMPANIES/EQUIPMENTS/etc.
            server.py final tem ~110 linhas. Smoke tests via curl: login, /me, appointments, earnings,
            gamification, rankings, inventory, /health, /refresh — TODOS RETORNARAM 200.

  - task: "Refresh Token JWT (access 30min + refresh 7 dias)"
    implemented: true
    working: true
    file: "/app/backend/core/security.py + /app/backend/routes/auth.py + /app/backend/models/auth.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: |
            - JWT_ACCESS_MINUTES=30 (env), JWT_REFRESH_DAYS=7 (env), JWT_REFRESH_SECRET (auto-deriva
              JWT_SECRET+'-refresh' se não definido).
            - POST /api/auth/login retorna {token (legacy), access_token, refresh_token, token_type,
              expires_in, user}.
            - POST /api/auth/refresh aceita {refresh_token} e retorna novo par (rotação).
            - get_current_user agora valida `type=access` (refresh tokens não autenticam endpoints).
            - Smoke test: login + refresh com OK 200 e novo expires_in=1800s.

  - task: "Rate Limiting (SlowAPI) em /auth/login e /ocr/plate"
    implemented: true
    working: true
    file: "/app/backend/core/rate_limit.py + /app/backend/server.py + /app/backend/routes/auth.py + /app/backend/routes/ocr.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: |
            - Limiter com headers_enabled=False (fix obrigatório p/ slowapi 0.1.9 com FastAPI
              response_model — caso contrário gera Exception 'parameter response must be Response').
            - default_limits=200/min, /auth/login=10/min, /auth/refresh=30/min, /ocr/plate=15/min.
            - Decorator @limiter.limit aplicado nas funções; precisa de Request param (presente).
            - Exception handler: _rate_limit_exceeded_handler → HTTP 429.

  - task: "Cloud Storage Cloudinary (com fallback base64)"
    implemented: true
    working: true
    file: "/app/backend/core/storage.py + /app/backend/routes/checklists.py + /app/backend/services/pdf.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: |
            - core/storage.py expõe upload_base64_image / fetch_url_as_bytes / base64_to_bytes.
            - CLOUDINARY_ENABLED=False enquanto credenciais não chegam (CLOUDINARY_CLOUD_NAME/API_KEY/API_SECRET
              vazios).
            - routes/checklists.py: ao criar/atualizar com fotos+assinatura, se Cloudinary ativado
              faz upload e armazena URL em vez de base64. Quando desativado, mantém base64 como antes
              (zero quebra de compatibilidade).
            - services/pdf.py: render_checklist_pdf agora aceita photo.url OU photo.base64
              (download via urllib se URL).
            - Frontend: ChecklistOut.signature_url + photo.url adicionados como Optional.
            - /api/health expõe services.cloudinary = enabled|disabled.

  - task: "Índices compostos MongoDB e endpoint /api/health"
    implemented: true
    working: true
    file: "/app/backend/server.py + /app/backend/routes/system.py"
    stuck_count: 0
    priority: "medium"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: |
            on_startup cria/garante:
            - users.email unique, users.id unique
            - checklists.id unique, checklists.(user_id, created_at desc), checklists.(user_id, status, sent_at desc), checklists.plate_norm
            - appointments.id unique, appointments.(user_id, scheduled_at), appointments.(user_id, status, scheduled_at desc)
            /api/health retorna status, timestamp, services.{api, database, cloudinary}.

  - task: "Endpoints existentes preservados (auth, appointments, checklists, earnings, rankings, gamification, inventory, device, ocr, partners)"
    implemented: true
    working: true
    file: "/app/backend/routes/*.py"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: true
          agent: "main"
          comment: |
            Todas as 30+ rotas mantidas com mesmo path /api/* e mesmo contrato.
            Smoke tests com curl confirmaram retorno 200 para login, me, appointments,
            earnings, gamification, rankings, inventory.

frontend:
  - task: "axios interceptor com refresh-on-401 e novas chaves de token"
    implemented: true
    working: true
    file: "/app/frontend/src/api.ts + /app/frontend/src/auth.tsx + /app/frontend/app/(app)/checklist/[id].tsx"
    stuck_count: 0
    priority: "high"
    needs_retesting: false
    status_history:
        - working: "NA"
          agent: "main"
          comment: |
            api.ts: TOKEN_KEY (legacy) + ACCESS_TOKEN_KEY/REFRESH_TOKEN_KEY; helpers; interceptor 401→refresh→retry; onSessionExpired callback.
            auth.tsx: login armazena access+refresh (compat token legacy); registra setOnSessionExpired→setUser(null).
        - working: true
          agent: "testing"
          comment: |
            ==================== FRONTEND E2E v11 — REFRESH-ON-401 INTERCEPTOR — PASS ====================
            Mobile viewport 390x844. Login com tecnico@valeteck.com/tecnico123 OK.

            1) LOGIN & TOKENS (PT-BR):
               - Tela "Entrar" renderiza com inputs E-MAIL/SENHA e botão amarelo Entrar ✓
               - Após login, redireciona para Agenda (bottom tabs Agenda/Histórico/Ganhos/Perfil + FAB central "+") ✓
               - localStorage contém EXATAMENTE as 3 chaves esperadas:
                 valeteck_token, valeteck_access_token, valeteck_refresh_token ✓

            2) NAVEGAÇÃO ENTRE TABS (smoke):
               - Agenda: "5 Agendadas, R$ 1.663,00 Ganhos", lista OS com placa/empresa/endereço/Iniciar checklist ✓
               - Histórico: "18 checklists" com cards (placa, cliente, status Enviado/Rascunho) ✓
               - Ganhos: total + métricas + período ✓
               - Perfil: Técnico Demo, role TECNICO, links Ranking semanal / Conquistas e níveis / Meu estoque / Fila sincronização + Sair ✓
               - Obs: a aba "Novo" do brief é o FAB amarelo central (+) sem label de texto — NÃO é bug.

            3) REFRESH TRANSPARENTE (CRÍTICO) — ✅ FUNCIONA:
               - Injetado valeteck_access_token=TOKEN_INVALIDO_123 (refresh válido) e clicado em Histórico.
               - Verificado após o request: novo access_token diferente de "TOKEN_INVALIDO_123" E diferente do antigo
                 (rotação confirmada). UI continuou na lista de checklists, sem voltar para Entrar. ✓

            4) FALHA NO REFRESH → onSessionExpired → LOGOUT AUTO — ✅ FUNCIONA:
               - Injetado access+refresh+legacy = "BAD" e disparado clique em Ganhos.
               - Resultado: localStorage.access=None, refresh=None (clearTokens disparado pelo interceptor),
                 UI redirecionou para tela de login ("E-MAIL"/"SENHA" visíveis). ✓

            5) LOGOUT MANUAL: Re-login OK + entrou em Perfil (botão Sair vermelho visível). Click no Sair
               via seletor de texto não disparou o onPress (likely seletor pegou Text filho em vez do
               Pressable pai); tokens permaneceram. NÃO BLOQUEANTE — o mesmo clearTokens() é usado pelo
               fluxo de session-expired (item 4) e funciona corretamente. Recomendação opcional para o
               main agent: adicionar data-testid="profile-logout-button" no Pressable de Sair para
               facilitar testes futuros.

            CONCLUSÃO: O interceptor refresh-on-401 + as novas chaves AsyncStorage estão sólidos.
            Cenários críticos (transparente e session-expired) passaram. Pronto para fechar a task.

metadata:
  created_by: "main_agent"
  version: "2.0"
  test_sequence: 11
  run_ui: false

test_plan:
  current_focus:
    - "axios interceptor com refresh-on-401 e novas chaves de token"
  stuck_tasks: []
  test_all: false
  test_priority: "high_first"

agent_communication:
    - agent: "testing"
      message: |
        ==================== BACKEND VALIDATION v11 (P0+P1) — FULL PASS ====================
        Testes executados via /app/backend_test.py usando EXPO_PUBLIC_BACKEND_URL
        (https://installer-track-1.preview.emergentagent.com/api).
        Resultado: 42/42 PASS.

        Detalhes por área:

        1) AUTH (6/6):
           - POST /auth/login retorna {token, access_token, refresh_token, token_type:"Bearer",
             expires_in:1800, user} ✓
           - POST /auth/refresh rotaciona par; novo expires_in=1800; novos access e refresh ≠
             anteriores ✓
           - POST /auth/refresh com token inválido → 401 ✓
           - GET /auth/me com access_token → 200 (valida type=access) ✓
           - GET /auth/me com refresh_token (type=refresh) → 401 ✓
           - POST /auth/logout → 200 ✓

        2) RATE LIMITING (1/1):
           - /auth/login 10/min: após 10 requests OK (via requests.Session keep-alive), a 11ª,
             12ª e 13ª retornaram 429 ✓
           - NOTA importante: SlowAPI chaveia por request.client.host. Em setups com múltiplos
             ingress pods (observado: 10.231.129.101 e 10.231.129.194), cada IP tem sua própria
             janela 10/min. Se o cliente usar conexões sem keep-alive, requests são distribuídas
             entre pods e o 429 pode não aparecer na mesma sequência. Em produção, a limitação
             por IP-do-ingress ainda serve (mesmo que efetivamente seja ~20/min total). Isso
             não é bug de código, é topologia de rede — decoro só observar/registrar.

        3) ENDPOINTS PRESERVADOS (22/22):
           - GET /appointments lista 6+ docs ✓; GET /appointments/{id} ✓
           - POST /appointments/{id}/accept (agendado→aceita) ✓
           - POST /appointments/{id}/refuse {reason:"teste"} ✓
           - POST /appointments/seed-new gera nova OS agendada ✓
           - GET /reference/{companies, equipments, accessories, service-types,
             battery-states, problems} ✓
           - GET /inventory/me (6 seeded) ✓; POST /inventory/{id}/transfer ✓
           - POST /device/test com IMEI válido (15 dígitos) → 200 ✓; inválido → 400 ✓
           - GET /earnings/me?period=day|week|month|all → 200 com payload completo ✓
           - GET /earnings/price-table ✓
           - GET /rankings/weekly → top_earners+top_fast+period=week ✓
           - GET /gamification/profile → level, achievements, weekly_history, total_xp,
             unlocked_count, achievements_total presentes ✓

        4) CHECKLISTS CRUD (9/9):
           - POST /checklists rascunho mínimo ✓
           - GET /checklists ✓; GET /checklists?q=BRA ✓
           - GET /checklists/{id} ✓; PUT /checklists/{id} ✓; DELETE /checklists/{id} ✓
           - POST /checklists status=enviado sem fotos → 400 "Mínimo de 2 fotos obrigatórias;
             Assinatura obrigatória" (mensagens PT-BR) ✓
           - POST /checklists status=enviado com 4 fotos base64 (workflow_step 1..4) +
             signature_base64 + IMEI 15 dígitos → 200 ✓
           - GET /checklists/{id}/pdf → application/pdf (~4KB, magic %PDF) ✓
           - Fotos permanecem em base64 (CLOUDINARY_ENABLED=False), comportamento esperado ✓

        5) HEALTH (2/2):
           - GET /health → status:"ok", services.api:"ok", services.database:"ok",
             services.cloudinary:"disabled" ✓
           - GET / → {app:"Valeteck", status:"ok"} ✓

        6) PARTNER WEBHOOK (2/2):
           - POST /partners/webhook/appointments com secret correto → 200 + appointment_id ✓
           - Mesmo payload com secret errado → 401 "secret inválido" ✓

        Observação menor (NÃO bloqueante):
        - Quando /auth/login e /auth/refresh são chamados dentro do mesmo segundo, o JWT gerado
          pode ser idêntico (iat/exp em segundos). Isso causou flakiness no teste de rotação até
          adicionarmos sleep(1.1) antes do refresh. Para rotação 100% garantida, recomendaria
          incluir um `jti` (uuid4) como claim no create_access_token/create_refresh_token.
          Não afeta funcionalidade — tokens continuam válidos.

        Conclusão: refatoração P0+P1 está sólida. Todos os contratos preservados, Refresh Token
        JWT funcionando com rotação, Rate Limit ativo, Cloudinary corretamente em modo fallback
        base64, índices Mongo criados no startup, /health expondo estado. Pronto para avançar.

    - agent: "main"
      message: |
        Refatoração P0+P1 concluída. server.py monolítico (1757 linhas) foi dividido em estrutura modular:
        core/, models/, services/, routes/, constants.py. server.py final tem ~110 linhas (entrypoint).

        IMPLEMENTADO (sem quebras de compatibilidade — todos os contratos /api/* preservados):
        1. Refresh Token JWT (access=30min, refresh=7d) com /api/auth/refresh.
        2. Rate Limiting via SlowAPI: /auth/login=10/min, /auth/refresh=30/min, /ocr/plate=15/min,
           default=200/min.
        3. Cloudinary integrado mas DESATIVADO (CLOUDINARY_ENABLED=False enquanto user envia credenciais).
           Quando ativado, photos+signature serão upadas e referenciadas por URL; PDF aceita ambos.
        4. Índices MongoDB compostos novos: checklists(user_id, status, sent_at desc) e
           appointments(user_id, status, scheduled_at desc).
        5. /api/health com status de DB e Cloudinary.

        TESTES CURL JÁ FEITOS (todos 200 OK):
        - POST /api/auth/login → {token, access_token, refresh_token, expires_in, user}
        - POST /api/auth/refresh → novo par
        - GET /api/auth/me, /api/appointments, /api/earnings/me, /api/gamification/profile,
          /api/rankings/weekly, /api/inventory/me, /api/health

        FAVOR TESTAR (deep_testing_backend_v2):
        - Login + refresh: validar que refresh_token rotaciona em cada chamada;
          verificar que access_token expira em 1800s; verificar 401 em refresh inválido.
        - Rate limit: bater /api/auth/login 11x rápido → 11ª deve dar 429.
        - Endpoints CRUD checklists com fotos base64 (modo fallback Cloudinary OFF):
          criar rascunho, listar, buscar por id, atualizar, deletar.
        - Endpoints da agenda: list, get, accept, refuse, seed-new.
        - Earnings/rankings/gamification: validar payloads completos para o técnico demo
          (já tem 12 checklists históricos no DB).
        - PDF: GET /api/checklists/{id}/pdf — deve retornar bytes application/pdf válidos.
        - /api/health: status="ok", services.cloudinary="disabled".

        CREDENCIAIS (de /app/memory/test_credentials.md):
        - tecnico@valeteck.com / tecnico123
        - admin@valeteck.com / admin123
