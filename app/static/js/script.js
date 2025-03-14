// Script para o AI Reader

document.addEventListener('DOMContentLoaded', function() {
    // Inicializa todos os tooltips
    var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'))
    var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl)
    });
    
    // Inicializa notificações
    const alerts = document.querySelectorAll('.alert-dismissible');
    alerts.forEach(alert => {
        setTimeout(() => {
            const bsAlert = new bootstrap.Alert(alert);
            bsAlert.close();
        }, 5000); // Fecha automaticamente depois de 5 segundos
    });
    
    // Validação de formulário de upload
    const pdfFileInput = document.getElementById('pdf_file');
    if (pdfFileInput) {
        pdfFileInput.addEventListener('change', function(e) {
            const file = e.target.files[0];
            if (file) {
                // Verifica se é um PDF
                if (file.type !== 'application/pdf') {
                    alert('Por favor, envie apenas arquivos PDF.');
                    e.target.value = '';
                    return;
                }
                
                // Verifica o tamanho máximo (16MB)
                const maxSize = 16 * 1024 * 1024; // 16MB em bytes
                if (file.size > maxSize) {
                    alert('O arquivo é muito grande. O tamanho máximo permitido é 16MB.');
                    e.target.value = '';
                }
            }
        });
    }
    
    // Animação para os cards na dashboard
    const cards = document.querySelectorAll('.card');
    cards.forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-5px)';
            this.style.boxShadow = '0 10px 20px rgba(0, 0, 0, 0.1)';
        });
        
        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
            this.style.boxShadow = '0 5px 15px rgba(0, 0, 0, 0.05)';
        });
    });
}); 