$('#data-table').DataTable({
	processing: true,
	serverSide: true,
	ajax: _url + "/sliders",
	"columns" : [
		
		{ data : "image", name : "image", className : "image" },
    	{ data : "title", name : "title", className : "title" },
    	{ data : "status", name : "status", className : "status" },
		{ data : "action", name : "action", orderable : false, searchable : false, className : "text-center" }
		
	],
	responsive: true,
	"bStateSave": true,
	"bAutoWidth":false,	
	"ordering": false
});