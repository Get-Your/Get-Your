

$(document).on('submit','#account-form',function(e){
    e.preventDefault();
    $.ajax({
        type : 'POST',
        url:'/application/account',
        data: $('#account-form').serialize(),
        success:function(data){
            if(data.result=="success")
            {
                alert('account created!');
                window.location = 'address';
            }
            else{
                alert(data.message)
            }
            
        },
        
        error: function (response) {
            console.log(response)
        },
    })
})

