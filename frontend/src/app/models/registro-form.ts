// src/app/models/registro-form.ts
// Interface para o formulário de registro (permite indexação por string)
export interface RegistroForm {
  data: string;
  humor: number;
  energia: number;
  estresse: number;
  sono_horas: number;
  qualidade_sono: number;
  alimentacao: number;
  avaliacao_geral: number;
  notas: string;
  [key: string]: string | number;  // permite acesso dinâmico pelo nome do campo
}

export function registroFormPadrao(data?: string): RegistroForm {
  return {
    data: data ?? new Date().toISOString().split('T')[0],
    humor: 5, energia: 5, estresse: 5, sono_horas: 7,
    qualidade_sono: 5, alimentacao: 5, avaliacao_geral: 5, notas: ''
  };
}
