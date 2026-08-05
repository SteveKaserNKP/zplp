" 1. Guards
if exists("b:current_syntax")
  finish
endif

syntax case ignore

" 2. Rules
" Structural blocks
syntax match zplpKeyword "\<\(DEF\|BEGIN_DOCUMENT\|END_DOCUMENT\|BEGIN_SECTION\|END_SECTION\|BEGIN_FIELD\|END_FIELD\)\>"

" Inner configuration settings
syntax match zplpSetting "\<\(POSITION\|FONT\|VALUE\|TYPE\|DPMM\|DIMENSIONS\|MARGINS\|BOX\|CODE39_CONFIG\|LINEAR_BARCODE_CONFIG\)\>"

" Constants following DEF
syntax match zplpConstant "\(\<DEF\s\+\)\@<=\w\+"

" Pointer variables starting with *
syntax match zplpPointer "\*\w\+"

" Numbers (Integers and Decimals)
syntax match zplpNumber "\<\d\+\(\.\d\+\)\?\>"

" Match everything after the constant name on a DEF line and force it to be one solid group
syntax match zplpDefValue "\(\<DEF\s\+\w\+\s\+\)\@<=.*$" contains=NONE

" Match the text on the left side of the double colons
syntax match zplpBracketKey "[A-Za-z0-9_]\+\ze::" contained

" Match the double colons explicitly
syntax match zplpBracketDelim "::" contained

" Match the text on the right side of the double colons
syntax match zplpBracketVal "\(\(::\)\@<=[^}]\+\)" contained

" Container: Everything else defaults to this color (the outer curly braces)
syntax region zplpBracketBlock start="{" end="}" contains=zplpBracketKey,zplpBracketDelim,zplpBracketVal

" Match everything after the word TYPE (ignoring spaces) up to the end of the line
syntax match zplpTypeValue "\(\<TYPE\s\+\)\@<=.*$" contains=NONE

" Comments
syntax region zplpComment start="//" end="$"
syntax region zplpBlockComment start="/#" end="#/"

" 3. Links
highlight def link zplpKeyword Statement
highlight def link zplpSetting Structure 
highlight def link zplpConstant PreProc
highlight def link zplpPointer PreProc
highlight def link zplpNumber Number
highlight def link zplpComment Comment
highlight def link zplpBlockComment Comment
highlight def link zplpBracketBlock Title
highlight def link zplpBracketDelim Title
highlight zplpBracketKey ctermfg=209
highlight zplpBracketVal ctermfg=209
highlight def link zplpDefValue String
highlight zplpTypeValue ctermfg=226

" 4. Mark Complete
let b:current_syntax = "zplp"

