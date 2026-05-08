<?php

require "vendor/autoload.php";
use PHPHtmlParser\Dom;

header('content-type: application/json');

postRequestCapture();



function postRequestCapture(){
    	
	$dom = new Dom;
	$dom->loadFromUrl('https://www.espn.in/nba/table');

	$details = array();

	$header_parent = $dom->find('.flex.flex-wrap.mv1');

	$groups = array();
	foreach($header_parent->find('.ButtonGroup a') AS $key => $group){
		if (($group->innerText ?? '') != '') {
			$groups[$key]['title'] = $group->innerText;
			$groups[$key]['value'] = strtolower($group->innerText);
		}
	}

	$years = array();
	foreach($header_parent->find('.dropdown.mr3 option') AS $key2 => $year){
		if (($year->innerText ?? '') != '' && ($year->getAttribute('value') ?? '') != '') {
			if(is_numeric($year->getAttribute('value'))){
				$years[$key2]['title'] = $year->innerText;
				$years[$key2]['value'] = $year->getAttribute('value');
			}
		}
	}

	$season_types = array();

	$season_types[0]['title'] = 'Regular Season';
	$season_types[0]['value'] = 'reg';

	$season_types[1]['title'] = 'Preseason';
	$season_types[1]['value'] = 'pre';

	$header = array('groups' => $groups, 'years' => $years, 'season_types' => $season_types);



	echo json_encode($header);
}