$('#data-table').DataTable({
	processing: true,
	serverSide: true,
	ajax: _url + "/categories",
	"columns" : [
		
		{ data : "image", name : "image", className : "image" },
    	{ data : "name", name : "name", className : "name" },
    	{ data : "total", name : "total", className : "total" },
    	{ data : "status", name : "status", className : "status" },
		{ data : "action", name : "action", orderable : false, searchable : false, className : "text-center" }
		
	],
	responsive: true,
	"bStateSave": true,
	"bAutoWidth":false,	
	"ordering": false
});