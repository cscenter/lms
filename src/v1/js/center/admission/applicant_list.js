import {createNotification} from "../../utils";

export default function initApplicantListSection() {
    $("._btn-import-testings-results").click(function () {
        if (this.getAttribute("disabled")) {
            return false;
        }
        $.ajax({
            type: "POST",
            url: this.href,
        }).done((data, textStatus, jqXHR) => {
            console.log(jqXHR);
           if (jqXHR.status === 201) {
               let msg = "Задание добавлено в очередь выполнения.";
               createNotification(msg);
               this.setAttribute("disabled", true);
           }
        }).fail(function () {
            let msg = "The number of errors in this code is too damn high. Sorry";
            createNotification(msg, 'error');
        });
        return false;
    })
}