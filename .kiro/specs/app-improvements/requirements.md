# Requirements Document

## Introduction

Esta especificação cobre quatro melhorias ao sistema de gestão de ativos IT (IT Asset Management), construído em Flask, PostgreSQL (via pymysql), templates Jinja2 e JavaScript puro:

1. **Registo de Utilizadores** — Criação de uma interface de gestão de utilizadores (listar, criar, editar, eliminar) que substitui a necessidade de inserção manual na base de dados.

2. **Paginação na Tabela de Assets** — Substituição do carregamento total dos registos por paginação do lado do servidor, garantindo desempenho estável à medida que o volume de dados cresce.

3. **Registo de Auditoria (Audit Log)** — Ligação do método `audit_log()` já existente em `rbac.py` às rotas de criação, edição e eliminação de assets, intervenções e técnicos, tornando todas as mutações rastreáveis.

4. **Gestão de Categorias** — Interface CRUD completa para gerir categorias de assets (adicionar, editar, eliminar), complementando a sua utilização existente nas consultas da aplicação.

## Glossary

- **Aplicação**: O sistema Flask de gestão de ativos IT.
- **Asset**: Equipamento ou recurso de IT registado no sistema, com campos como `asset_tag`, `name`, `brand`, `model`, `category_id` e `status`.
- **Utilizador**: Entidade autenticada no sistema, armazenada na tabela `users`, com campos `id`, `username`, `password` e `role_id`.
- **Role**: Papel atribuído a um utilizador (ex: Admin, Técnico, Utilizador), armazenado na tabela `roles`.
- **Categoria**: Agrupamento funcional de assets (ex: Laptop, Monitor, Servidor), armazenado na tabela `categories` com campos `id` e `name`.
- **Intervenção**: Registo de manutenção associado a um asset e a um técnico, armazenado na tabela `interventions`.
- **Técnico**: Colaborador responsável por intervenções, armazenado na tabela `technicians`.
- **Audit_Log**: Tabela `audit_log` que regista ações de mutação sobre entidades do sistema, com campos `user_id`, `action`, `entity_type`, `entity_id`, `old_value`, `new_value` e `timestamp`.
- **RBAC_Manager**: Classe `RBACManager` em `rbac.py` que expõe o método `audit_log()` para registar entradas na `Audit_Log`.
- **Session**: Sessão Flask ativa que mantém o estado de autenticação do utilizador corrente, incluindo `session['user']` e opcionalmente `session['user_id']`.
- **Assets_Route**: Rota Flask `/assets` que devolve a lista paginada de assets.
- **Assets_Table**: Tabela HTML na página `/assets` que lista os assets da página corrente.
- **Pagination_Bar**: Componente de navegação entre páginas exibido abaixo da **Assets_Table**.
- **Users_Route**: Conjunto de rotas Flask para gestão de utilizadores, sob o prefixo `/users`.
- **Users_Table**: Tabela HTML na página `/users` que lista todos os utilizadores registados.
- **Categories_Route**: Conjunto de rotas Flask para gestão de categorias, sob o prefixo `/categories`.
- **Categories_Table**: Tabela HTML na página `/categories` que lista todas as categorias registadas.

---

## Requirements

### Requirement 1: Gestão de Utilizadores

**User Story:** Como administrador, quero gerir utilizadores através de uma interface web, para criar, editar e remover contas sem aceder diretamente à base de dados.

#### Acceptance Criteria

1. WHILE o administrador tem sessão autenticada, THE **Users_Route** SHALL disponibilizar uma página em `/users` que lista todos os utilizadores registados na tabela `users`, exibindo pelo menos o `id`, `username` e o nome da `role` associada.

2. WHEN o administrador submete o formulário de criação com `username` entre 1 e 50 caracteres, `password` com pelo menos 8 caracteres e um `role_id` que existe na tabela `roles`, THE **Users_Route** SHALL inserir um novo registo na tabela `users` com a `password` armazenada como hash bcrypt e redirecionar para `/users`.

3. IF o `username` submetido no formulário de criação já existir na tabela `users` (comparação insensível a maiúsculas/minúsculas), THEN THE **Users_Route** SHALL devolver a página de criação com uma mensagem de erro indicando que o nome de utilizador já está em uso, sem inserir o registo duplicado.

4. IF o `username` for vazio, tiver mais de 50 caracteres, ou a `password` tiver menos de 8 caracteres, ou o `role_id` não existir na tabela `roles`, THEN THE **Users_Route** SHALL devolver a página de criação com uma mensagem de erro descrevendo a validação que falhou, sem inserir o registo.

5. WHEN o administrador submete o formulário de edição de um utilizador existente com um `role_id` que existe na tabela `roles`, THE **Users_Route** SHALL atualizar o `role_id` do utilizador na base de dados e redirecionar para `/users`.

6. WHERE o formulário de edição inclui um campo de nova `password`, WHEN esse campo não está vazio e tem pelo menos 8 caracteres, THE **Users_Route** SHALL atualizar a `password` do utilizador com o hash bcrypt do valor fornecido.

7. WHEN o administrador solicita a eliminação de um utilizador cujo `username` não corresponde ao `session['user']` corrente, THE **Users_Route** SHALL eliminar o registo da tabela `users` e redirecionar para `/users`.

8. IF o administrador tentar eliminar o utilizador cujo `username` é igual ao `session['user']` corrente, THEN THE **Users_Route** SHALL rejeitar a operação e devolver uma mensagem de erro indicando que não é possível eliminar a própria conta.

9. IF o `id` de utilizador fornecido numa operação de edição ou eliminação não existir na tabela `users`, THEN THE **Users_Route** SHALL devolver uma mensagem de erro sem alterar nenhum registo.

10. THE **Users_Table** SHALL apresentar um botão ou ligação de edição e um botão de eliminação por cada linha de utilizador.

---

### Requirement 2: Paginação na Tabela de Assets

**User Story:** Como utilizador autenticado, quero que a tabela de assets carregue apenas um subconjunto de registos por página, para que a aplicação se mantenha responsiva independentemente do volume total de assets.

#### Acceptance Criteria

1. WHEN a página `/assets` é carregada sem parâmetro `page`, THE **Assets_Route** SHALL devolver a primeira página de resultados com 20 assets por página, por omissão.

2. WHEN a página `/assets` é carregada com o parâmetro de consulta `page=N` (inteiro positivo), THE **Assets_Route** SHALL devolver os assets correspondentes ao offset `(N-1) * 20` e ao limite `20`, ordenados por `id DESC`.

3. IF o parâmetro `page` estiver ausente, não for numérico, não for um inteiro, for zero ou for negativo, THEN THE **Assets_Route** SHALL tratar o valor como `1` e devolver a primeira página de resultados, sem devolver um erro ao utilizador.

4. IF o parâmetro `page` for superior ao número total de páginas disponíveis para os filtros ativos, THEN THE **Assets_Route** SHALL devolver a última página de resultados disponível, sem devolver um erro ao utilizador.

5. THE **Assets_Route** SHALL calcular o número total de assets que satisfazem os filtros ativos e passar esse valor ao template para permitir a renderização da **Pagination_Bar**.

6. THE **Pagination_Bar** SHALL exibir ligações para a página anterior, a página seguinte e pelo menos 1 página adjacente de cada lado da página corrente, sendo a ligação "anterior" renderizada como não clicável na primeira página e a ligação "seguinte" renderizada como não clicável na última página.

7. WHILE o utilizador está a visualizar a tabela de assets com filtros ativos (estado, categoria, marca, texto), THE **Assets_Route** SHALL aplicar a paginação sobre o subconjunto filtrado, garantindo que os filtros são preservados nos parâmetros de consulta das ligações de paginação.

8. WHEN o utilizador altera um filtro na página `/assets`, THE **Assets_Route** SHALL repor a paginação na página `1` para o novo conjunto de resultados filtrados.

---

### Requirement 3: Registo de Auditoria

**User Story:** Como administrador, quero que todas as operações de criação, edição e eliminação de assets, intervenções e técnicos sejam registadas automaticamente no audit log, para poder rastrear quem fez o quê e quando.

#### Acceptance Criteria

1. WHEN um asset é criado com sucesso, THE **RBAC_Manager** SHALL registar na **Audit_Log** uma entrada com `action='CREATE'`, `entity_type='asset'`, `entity_id` igual ao `id` do asset criado, `new_value` com todos os campos não nulos do asset, e `user_id` do utilizador da **Session** corrente.

2. WHEN um asset é editado com sucesso, THE **RBAC_Manager** SHALL registar na **Audit_Log** uma entrada com `action='UPDATE'`, `entity_type='asset'`, `entity_id` do asset, `user_id` do utilizador da **Session** corrente, `old_value` com os valores anteriores e `new_value` com os valores atualizados.

3. WHEN um asset é eliminado com sucesso, THE **RBAC_Manager** SHALL registar na **Audit_Log** uma entrada com `action='DELETE'`, `entity_type='asset'`, `entity_id` do asset eliminado, `user_id` do utilizador da **Session** corrente, e `old_value` com todos os campos não nulos do asset antes da eliminação.

4. WHEN uma intervenção é criada com sucesso, THE **RBAC_Manager** SHALL registar na **Audit_Log** uma entrada com `action='CREATE'`, `entity_type='intervention'`, `entity_id` da intervenção criada, `new_value` com todos os campos não nulos da intervenção, e `user_id` do utilizador da **Session** corrente.

5. WHEN uma intervenção é concluída com sucesso, THE **RBAC_Manager** SHALL registar na **Audit_Log** uma entrada com `action='UPDATE'`, `entity_type='intervention'`, `entity_id` da intervenção, `user_id` do utilizador da **Session** corrente, `old_value='Active'` e `new_value='Completed'`.

6. WHEN uma intervenção é eliminada com sucesso, THE **RBAC_Manager** SHALL registar na **Audit_Log** uma entrada com `action='DELETE'`, `entity_type='intervention'`, `entity_id` da intervenção eliminada, `user_id` do utilizador da **Session** corrente, e `old_value` com os campos não nulos da intervenção antes da eliminação.

7. WHEN um técnico é criado com sucesso, THE **RBAC_Manager** SHALL registar na **Audit_Log** uma entrada com `action='CREATE'`, `entity_type='technician'`, `entity_id` do técnico criado, `new_value` com todos os campos não nulos do técnico, e `user_id` do utilizador da **Session** corrente.

8. WHEN um técnico é eliminado com sucesso, THE **RBAC_Manager** SHALL registar na **Audit_Log** uma entrada com `action='DELETE'`, `entity_type='technician'`, `entity_id` do técnico eliminado, `user_id` do utilizador da **Session** corrente, e `old_value` com os campos não nulos do técnico antes da eliminação.

9. IF o método `audit_log()` do **RBAC_Manager** falhar ao registar uma entrada, THEN THE **Aplicação** SHALL completar a operação principal (criação, edição ou eliminação da entidade) sem reverter a transação, e SHALL registar o erro de auditoria no log de sistema via `app.logger.error`.

10. WHEN a página `/audit-log` é carregada, THE **Aplicação** SHALL devolver uma página que lista as entradas da **Audit_Log** ordenadas por `timestamp` decrescente, exibindo pelo menos `timestamp`, `username`, `action`, `entity_type`, `entity_id`, `old_value` e `new_value`, mostrando apenas entradas cujo `user_id` tem correspondência na tabela `users`.

---

### Requirement 4: Gestão de Categorias

**User Story:** Como administrador, quero gerir as categorias de assets através de uma interface web, para adicionar, editar e remover categorias sem aceder diretamente à base de dados.

#### Acceptance Criteria

1. WHILE o administrador tem sessão autenticada, THE **Categories_Route** SHALL disponibilizar uma página em `/categories` que lista todas as categorias registadas na tabela `categories`, exibindo pelo menos o `id`, o `name` e o número de assets associados.

2. WHEN o administrador submete o formulário de criação com um `name` entre 1 e 100 caracteres (após remoção de espaços iniciais e finais) e esse `name` não existir na tabela `categories` (comparação insensível a maiúsculas/minúsculas), THE **Categories_Route** SHALL inserir um novo registo na tabela `categories` com o valor trimmed do `name` e redirecionar para `/categories`.

3. IF o `name` submetido no formulário de criação for vazio ou contiver apenas espaços em branco após trimming, THEN THE **Categories_Route** SHALL devolver a página com uma mensagem de erro sem inserir o registo.

4. IF o `name` submetido no formulário de criação tiver mais de 100 caracteres após trimming, THEN THE **Categories_Route** SHALL devolver a página com uma mensagem de erro indicando o limite de caracteres, sem inserir o registo.

5. IF o `name` submetido no formulário de criação já existir na tabela `categories` (comparação insensível a maiúsculas/minúsculas), THEN THE **Categories_Route** SHALL devolver a página com uma mensagem de erro indicando que a categoria já existe, sem inserir o registo duplicado.

6. WHEN o administrador submete o formulário de edição de uma categoria existente com um `name` entre 1 e 100 caracteres (após trimming) e esse `name` não existir noutra categoria, THE **Categories_Route** SHALL atualizar o `name` na tabela `categories` com o valor trimmed e redirecionar para `/categories`.

7. IF o `name` submetido no formulário de edição for vazio, contiver apenas espaços em branco, ou tiver mais de 100 caracteres após trimming, THEN THE **Categories_Route** SHALL devolver a página de edição com uma mensagem de erro, sem atualizar o registo.

8. IF o `name` submetido no formulário de edição já existir noutra categoria (comparação insensível a maiúsculas/minúsculas, excluindo a própria categoria editada), THEN THE **Categories_Route** SHALL devolver a página de edição com uma mensagem de erro indicando que o nome já está em uso, sem atualizar o registo.

9. WHEN o administrador solicita a eliminação de uma categoria que não tem assets associados, THE **Categories_Route** SHALL eliminar o registo da tabela `categories` e redirecionar para `/categories`.

10. IF o administrador tentar eliminar uma categoria que tem um ou mais assets associados, THEN THE **Categories_Route** SHALL rejeitar a operação e devolver uma mensagem de erro indicando o número de assets que impedem a eliminação.

11. IF o `id` de categoria fornecido numa operação de edição ou eliminação não existir na tabela `categories`, THEN THE **Categories_Route** SHALL devolver uma mensagem de erro sem alterar nenhum registo.

12. THE **Categories_Table** SHALL apresentar um botão ou ligação de edição e um botão de eliminação por cada linha de categoria.
