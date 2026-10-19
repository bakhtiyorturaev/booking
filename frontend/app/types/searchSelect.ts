export interface SearchSelectOption {
  value: string
  label: string
  description?: string
}

export interface SearchSelectPage {
  options: SearchSelectOption[]
  hasNext: boolean
}
