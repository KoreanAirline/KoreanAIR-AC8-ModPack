option casemap:none
EXTERN observe_saved_frame:PROC
EXTERN invoke_caller_rsp:QWORD
EXTERN expected_nonvolatile:QWORD
EXTERN abi_step_mode:BYTE
PUBLIC invoke_psm
PUBLIC invoke_start
PUBLIC invoke_return
PUBLIC invoke_end
PUBLIC clobber_helper
PUBLIC tail_probe
.code
invoke_psm PROC FRAME
invoke_start LABEL BYTE
    push r12
    .pushreg r12
    push r13
    .pushreg r13
    push r14
    .pushreg r14
    sub rsp,30h
    .allocstack 30h
    .endprolog
    mov r14,rcx
    mov r12,rdx
    mov r13,r8
    mov [invoke_caller_rsp],rsp
    mov [expected_nonvolatile],rbx
    mov [expected_nonvolatile+8],rsi
    mov [expected_nonvolatile+16],rdi
    mov [expected_nonvolatile+24],rbp
    mov rax,[r12+0A0h]
    mov [rsp+20h],rax
    movdqu xmm0,[r12+40h]
    movdqu xmm1,[r12+50h]
    movdqu xmm2,[r12+60h]
    movdqu xmm3,[r12+70h]
    movdqu xmm4,[r12+80h]
    movdqu xmm5,[r12+90h]
    mov rcx,[r12+8]
    mov rdx,[r12+10h]
    mov r8,[r12+18h]
    mov r9,[r12+20h]
    mov r10,[r12+28h]
    mov r11,[r12+30h]
    push qword ptr [r12+38h]
    popfq
    mov rax,[r12]
    call r14
invoke_return LABEL BYTE
    mov [r13],rax
    mov [r13+8],rcx
    mov [r13+10h],rdx
    mov [r13+18h],r8
    mov [r13+20h],r9
    mov [r13+28h],r10
    mov [r13+30h],r11
    pushfq
    pop qword ptr [r13+38h]
    movdqu [r13+40h],xmm0
    movdqu [r13+50h],xmm1
    movdqu [r13+60h],xmm2
    movdqu [r13+70h],xmm3
    movdqu [r13+80h],xmm4
    movdqu [r13+90h],xmm5
    add rsp,30h
    pop r14
    pop r13
    pop r12
    ret
invoke_end LABEL BYTE
invoke_psm ENDP
clobber_helper PROC FRAME
    sub rsp,28h
    .allocstack 28h
    .endprolog
    call observe_saved_frame
    mov byte ptr [rsp+20h],al
    mov rax,0F1F1F1F1F1F1F100h
    mov rcx,0F2F2F2F2F2F2F2F2h
    mov rdx,0F3F3F3F3F3F3F3F3h
    mov r8,0F4F4F4F4F4F4F4F4h
    xor r9,r9
    mov r10,0F6F6F6F6F6F6F6F6h
    mov r11,0F7F7F7F7F7F7F7F7h
    pcmpeqd xmm0,xmm0
    pcmpeqd xmm1,xmm1
    pcmpeqd xmm2,xmm2
    pcmpeqd xmm3,xmm3
    pcmpeqd xmm4,xmm4
    pcmpeqd xmm5,xmm5
    mov al,byte ptr [rsp+20h]
    add rsp,28h
    cmp byte ptr [abi_step_mode],0
    je helper_return
    pushfq
    or qword ptr [rsp],100h
    popfq
helper_return:
    ret
clobber_helper ENDP
tail_probe PROC
    ret
tail_probe ENDP
END
