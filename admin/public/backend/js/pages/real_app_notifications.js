$('#data-table').DataTable({
        processing: true,
        serverSide: true,
        ajax: _url + "/real_app_notifications",
        "columns" : [

        { data : "title", name : "title", className: 'details-control', responsivePriority: 1 },
        { data : "created_at", name : "created_at", className : "created_at" },
        { data : "action", name : "action", orderable : false, searchable : false, className : "text-center" }

        ],
        responsive: true,
        "bStateSave": true,
        "bAutoWidth":false, 
        "ordering": false
    });