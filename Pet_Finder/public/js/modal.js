function abrirModalProcura() {
    const modal = document.getElementById('janela-modal-procura');
    modal.classList.add('abrir');

    modal.addEventListener('click', (e) => {
        if (e.target.id === 'fechar-procura' || e.target.id === 'janela-modal-procura') {
            modal.classList.remove('abrir');
        }
    });
}

function abrirModalAchei() {
    const modalAchei = document.getElementById('janela-modal-encontrei');
    modalAchei.classList.add('abrir');

    modalAchei.addEventListener('click', (e) => {
        if (e.target.id === 'fechar-encontrei' || e.target.id === 'janela-modal-encontrei') {
            modalAchei.classList.remove('abrir');
        }
    });
}
