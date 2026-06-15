# Requirements Document

## Introduction

Esta funcionalidade melhora o sistema de gestão de ativos IT (IT Asset Management) em dois eixos complementares:

1. **Gráfico no Dashboard** — formalizar e garantir a renderização correta de um gráfico de barras com a distribuição de assets por estado (Active, Maintenance, Inactive), usando Chart.js, com dados provenientes diretamente da base de dados PostgreSQL.

2. **Filtros na Tabela de Assets** — consolidar e completar os mecanismos de filtragem dinâmica da tabela de assets, permitindo filtrar por estado, categoria e marca sem recarregar a página, incluindo pesquisa por texto livre e feedback visual da contagem de resultados.

O projeto usa Flask (Python), PostgreSQL, templates Jinja2/HTML e JavaScript estático. Não são introduzidas novas dependências externas — Chart.js já está referenciado no dashboard e a filtragem é feita no cliente via JavaScript puro.

## Glossary

- **Dashboard**: Página principal da aplicação, acessível em `/dashboard`, que apresenta métricas agregadas do sistema.
- **Asset**: Equipamento ou recurso de IT registado no sistema, com campos como `asset_tag`, `name`, `brand`, `model`, `category_id` e `status`.
- **Estado (Status)**: Valor enumerado de um asset. Os valores válidos são `Active`, `Maintenance` e `Inactive`.
- **Categoria**: Agrupamento funcional de assets (ex: Laptop, Monitor, Servidor), proveniente da tabela `categories`.
- **Marca (Brand)**: Campo `brand` de um asset que identifica o fabricante.
- **Chart.js**: Biblioteca JavaScript de gráficos, já carregada via CDN no `dashboard.html`.
- **Dashboard_Route**: Rota Flask `/dashboard` que recolhe métricas da BD e passa os dados ao template.
- **Assets_Route**: Rota Flask `/assets` que devolve a lista completa de assets com as respetivas categorias.
- **Assets_Table**: Tabela HTML na página `/assets` que lista todos os assets registados.
- **Filter_Bar**: Barra de controlos de filtragem na página de assets, contendo campo de pesquisa e seletores de estado, categoria e marca.
- **Status_Chart**: Gráfico de barras no dashboard que mostra a distribuição de assets por estado.

---

## Requirements

### Requirement 1: Gráfico de Barras de Assets por Estado no Dashboard

**User Story:** Como utilizador autenticado, quero ver um gráfico de barras no dashboard que mostre o número de assets em cada estado, para compreender rapidamente a distribuição do parque informático sem consultar tabelas.

#### Acceptance Criteria

1. THE **Dashboard_Route** SHALL passar ao template `dashboard.html` as variáveis `active_assets`, `maintenance_assets`, `inactive_assets` e `total_assets` com os valores contados diretamente da base de dados.

2. WHEN a página `/dashboard` é carregada, THE **Status_Chart** SHALL renderizar um gráfico de barras com três barras correspondentes aos estados `Active`, `Maintenance` e `Inactive`.

3. WHEN a página `/dashboard` é carregada, THE **Status_Chart** SHALL atribuir a cada barra uma cor distinta: verde (`#1cc88a`) para Active, amarelo (`#f6c23e`) para Maintenance e vermelho (`#e74a3b`) para Inactive.

4. WHILE o utilizador está autenticado, THE **Status_Chart** SHALL exibir valores inteiros não negativos em cada barra, correspondendo exatamente aos contadores devolvidos pela **Dashboard_Route**.

5. THE **Dashboard_Route** SHALL garantir que a soma de `active_assets` + `maintenance_assets` + `inactive_assets` é igual a `total_assets` em todos os estados consistentes da base de dados. WHEN as contagens retornadas pelas queries divergirem devido a modificações concorrentes, THE **Dashboard_Route** SHALL exibir os valores devolvidos pelas queries sem bloquear a renderização da página.

6. IF a base de dados não contiver nenhum asset num determinado estado, THEN THE **Status_Chart** SHALL exibir o valor `0` para esse estado, sem erro de renderização.

7. WHEN um asset é adicionado, editado ou removido, THE **Dashboard_Route** SHALL refletir os novos contadores na próxima vez que a página `/dashboard` for carregada.

---

### Requirement 2: Filtragem de Assets por Estado

**User Story:** Como utilizador autenticado, quero filtrar a tabela de assets por estado (Active, Maintenance, Inactive), para visualizar rapidamente apenas os assets relevantes para uma determinada ação operacional.

#### Acceptance Criteria

1. THE **Filter_Bar** SHALL apresentar um seletor com as opções `All Status`, `Active`, `Maintenance` e `Inactive`.

2. WHEN o utilizador seleciona um estado no seletor, THE **Assets_Table** SHALL ocultar todas as linhas cujo atributo `data-status` não corresponda ao valor selecionado, sem recarregar a página.

3. WHEN o utilizador seleciona a opção `All Status`, THE **Assets_Table** SHALL tornar visíveis todas as linhas previamente ocultas pelo filtro de estado.

4. THE **Assets_Route** SHALL incluir o atributo `data-status` em cada linha `<tr>` da **Assets_Table**, com o valor exato do campo `status` do asset correspondente. IF uma linha não contiver o atributo `data-status`, THEN THE **Assets_Table** SHALL renderizar essa linha normalmente e tratá-la como não filtrada, não bloqueando a exibição da tabela.

---

### Requirement 3: Filtragem de Assets por Categoria

**User Story:** Como utilizador autenticado, quero filtrar a tabela de assets por categoria, para identificar rapidamente todos os assets de um tipo específico (ex: todos os laptops).

#### Acceptance Criteria

1. THE **Filter_Bar** SHALL apresentar um seletor de categorias preenchido dinamicamente com as categorias únicas presentes na **Assets_Table**, precedidas pela opção `All Categories`.

2. WHEN o utilizador seleciona uma categoria no seletor, THE **Assets_Table** SHALL ocultar todas as linhas cujo atributo `data-category` não corresponda ao valor selecionado, sem recarregar a página.

3. WHEN o utilizador seleciona a opção `All Categories`, THE **Assets_Table** SHALL tornar visíveis todas as linhas previamente ocultas pelo filtro de categoria.

4. THE **Assets_Route** SHALL incluir o atributo `data-category` em cada linha `<tr>` da **Assets_Table**, com o valor do nome de categoria (`category_name`) do asset. WHEN o asset não tem categoria atribuída, THE **Assets_Route** SHALL definir o atributo `data-category` com valor vazio.

---

### Requirement 4: Filtragem de Assets por Marca

**User Story:** Como utilizador autenticado, quero filtrar a tabela de assets por marca, para localizar todos os equipamentos de um fabricante específico.

#### Acceptance Criteria

1. THE **Filter_Bar** SHALL apresentar um seletor de marcas preenchido dinamicamente com as marcas únicas presentes na **Assets_Table**, precedidas pela opção `All Brands`.

2. WHEN o utilizador seleciona uma marca no seletor, THE **Assets_Table** SHALL ocultar todas as linhas cujo atributo `data-brand` não corresponda ao valor selecionado, sem recarregar a página.

3. WHEN o utilizador seleciona a opção `All Brands`, THE **Assets_Table** SHALL tornar visíveis todas as linhas previamente ocultas pelo filtro de marca.

4. THE **Assets_Route** SHALL incluir o atributo `data-brand` em cada linha `<tr>` da **Assets_Table**, com o valor do campo `brand` do asset. WHEN o asset não tem marca definida, THE **Assets_Route** SHALL definir o atributo `data-brand` com valor vazio.

---

### Requirement 5: Pesquisa por Texto Livre na Tabela de Assets

**User Story:** Como utilizador autenticado, quero pesquisar assets por texto livre, para localizar rapidamente um asset específico pelo seu nome, tag, modelo ou qualquer outro campo visível.

#### Acceptance Criteria

1. THE **Filter_Bar** SHALL apresentar um campo de texto com placeholder descritivo que aceite qualquer sequência de caracteres como termo de pesquisa.

2. WHEN o utilizador introduz texto no campo de pesquisa, THE **Assets_Table** SHALL ocultar todas as linhas cujo conteúdo textual visível não contenha a sequência de caracteres introduzida (insensível a maiúsculas/minúsculas), sem recarregar a página. WHEN uma nova linha é adicionada à tabela enquanto existe texto no campo de pesquisa, THE **Assets_Table** SHALL ocultar imediatamente essa linha se o seu conteúdo não contiver o termo de pesquisa ativo.

3. WHEN o campo de pesquisa é esvaziado, THE **Assets_Table** SHALL tornar visíveis todas as linhas previamente ocultas pela pesquisa de texto.

---

### Requirement 6: Filtragem Combinada e Contagem de Resultados

**User Story:** Como utilizador autenticado, quero aplicar múltiplos filtros em simultâneo e ver quantos assets correspondem aos critérios ativos, para ter uma visão precisa do subconjunto de assets que me interessa.

#### Acceptance Criteria

1. WHEN múltiplos filtros estão ativos em simultâneo, THE **Assets_Table** SHALL exibir apenas as linhas que satisfazem todos os critérios ativos (interseção: estado AND categoria AND marca AND texto).

2. THE **Filter_Bar** SHALL apresentar um contador de resultados que indica o número de linhas atualmente visíveis na **Assets_Table**.

3. WHEN os valores dos filtros são alterados, THE **Filter_Bar** SHALL atualizar o contador de resultados imediatamente, sem recarregar a página.

4. WHEN todos os filtros são redefinidos para os seus valores por omissão (`All Status`, `All Categories`, `All Brands`, campo de texto vazio), THE **Assets_Table** SHALL exibir todas as linhas e o contador SHALL refletir o número total de assets.

5. IF a combinação de filtros ativos não corresponder a nenhuma linha da **Assets_Table**, THEN THE **Assets_Table** SHALL exibir uma mensagem informativa indicando que não foram encontrados assets correspondentes.
