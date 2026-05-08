<?php

require "vendor/autoload.php";
use PHPHtmlParser\Dom;

header('content-type: application/json');

$data = array();

$data['season_type'] = 'reg';
$data['season'] = '2021';
$data['group'] = 'division';

postRequestCapture($data);



function postRequestCapture($data){

	$season_type = $data['season_type'];
	$season = $data['season'];
	$group = $data['group'];
    	
	$dom = new Dom;
	$dom->loadFromUrl("https://www.espn.in/nba/table/_/seasontype/$season_type/season/$season/group/$group");

	$details = array();


	$standings = array();
	foreach ($dom->find('.standings__table') as $key => $standing) {

		$standings[$key]['title'] = $standing->find('.Table__Title')->innerText ?? '';
		$standings[$key]['standing'] = array();

		$team = array();
		foreach ($standing->find('.flex > table tbody tr') as $key2 => $standing2) {
			
			$team[$key2]['is_group'] = 'no';
			if (($team[$key2]['name'] = $standing2->find('.hide-mobile > a', 0)->innerText ?? '') == '') {
				$team[$key2]['is_group'] = 'yes';
				$team[$key2]['name'] = $standing2->find('.fw-medium.w-100.dib', 0)->innerText ?? '';
			}else{
				$team[$key2]['name'] = $standing2->find('.hide-mobile > a', 0)->innerText ?? '';
			}

			$team[$key2]['short_name'] = $standing2->find('.dn.show-mobile abbr', 0)->innerText ?? '';
			$team[$key2]['prefix'] = $standing2->find('.dib.pl1', 0)->innerText ?? '';
			$team[$key2]['logo'] = '';
			if($team[$key2]['short_name']){
				$team[$key2]['logo'] = "https://a.espncdn.com/combiner/i?img=/i/teamlogos/nba/500/scoreboard/" . strtolower($team[$key2]['short_name']) . ".png&h=40&w=40";
			}

			$team[$key2]['position'] = $standing2->find('.team-position', 0)->innerText ?? '';
		}

		$points = array();

		foreach ($standing->find('.Table__Scroller tbody tr') as $key3 => $standing3) {
			
			$columns = $standing3->find('td');
			$points[$key3] = $team[$key3];
			$points[$key3]['w'] =  $columns[0]->innerText ?? '';
			$points[$key3]['l'] =  $columns[1]->innerText ?? '';
			$points[$key3]['pct'] =  $columns[2]->innerText ?? '';
			$points[$key3]['gb'] =  $columns[3]->innerText ?? '';
			$points[$key3]['home'] =  $columns[4]->innerText ?? '';
			$points[$key3]['away'] =  $columns[5]->innerText ?? '';
			$points[$key3]['div'] =  $columns[6]->innerText ?? '';
			$points[$key3]['conf'] =  $columns[7]->innerText ?? '';
			$points[$key3]['ppg'] =  $columns[8]->innerText ?? '';
			$points[$key3]['opp_ppg'] =  $columns[9]->innerText ?? '';
			$points[$key3]['diff'] =  $columns[10]->innerText ?? '';
			$points[$key3]['strk'] =  $columns[11]->innerText ?? '';
			$points[$key3]['l10'] =  $columns[12]->innerText ?? '';
			$standings[$key]['standing'] = $points;
		}
		//$name = 



	}


	echo json_encode($standings);
}