/*
Get-Your is a platform for application and administration of income-
qualified programs, used primarily by the City of Fort Collins.
Copyright (C) 2023

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

This program is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with this program.  If not, see <https://www.gnu.org/licenses/>.
*/

$(document).on('submit', '#account-form', function (e) {
    e.preventDefault();
    $.ajax({
        type: 'POST',
        url: $('#account-form').attr('action'),
        data: $('#account-form').serialize(),
        success: function (data) {
            if (data.result === "success") {
                alert('account created!');
                window.location = 'address';
            } else if ("redirect" in data) {
                window.location.href = data.redirect;
            } else {
                alert(data.message)
            }
        },

        error: function (response) {
            console.log(response)
        },
    });
});

// Check for when the document is ready
$(document).ready(function () {
    // When a checkbox is clicked, call the toggleBtnState() function
    $("input[type=checkbox]").click(function () {
        toggleBtnState();
    });

    // Check if any of the input[type=checkbox] are checked when the page
    // is ready.
    setTimeout(function () {
        toggleBtnState();
    }, 500);
});

// toggleBtnState() is called when a checkbox is clicked
function toggleBtnState() {
    // Check if any of the input[type=checkbox] are checked, except for the
    // one with the id of "id_Identification"
    // If they are, enable the button and change the text to "Continue"
    // If they are not, disable the button and change the text to "Select a Program"
    if ($("input[type=checkbox]:checked").not("#id_Identification").length > 0) {
        $("#btnContinue").prop("disabled", false);
        $("#btnContinue").html("CONTINUE");
    } else {
        $("#btnContinue").prop("disabled", true);
        $("#btnContinue").html("SELECT A PROGRAM");
    }
}
