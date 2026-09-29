## O que muda

<!-- Uma ou duas frases. -->

## Item do checklist

Fecha #

## Como testar

1. `.venv/bin/pip install -r requirements.txt`
2. `.venv/bin/pytest -ra`
3. `.venv/bin/uvicorn app.web:app --port 8765` e abrir as telas afetadas:
   - [ ] a 1280px
   - [ ] a 375px, sem rolagem horizontal

## Conferência antes de aprovar

- [ ] CI verde, nenhum teste pulado sem motivo escrito
- [ ] Nenhum segredo, token ou dado real de empresa no diff
- [ ] Telas seguem a paleta da Meta e o padrão de sites (sem sombra, uma cor de ação)
- [ ] Seção do relatório afetada foi atualizada em `docs/`
