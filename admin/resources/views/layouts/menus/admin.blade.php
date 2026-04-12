<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="{{ url('free_tips') }}">
		<i class="fa fa-lightbulb u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('Free Tips') }}</span>
	</a>
</li>
<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="{{ url('another_tips') }}">
		<i class="fa fa-lightbulb u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('2 Odds Tips') }}</span>
	</a>
</li>
<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="{{ url('tips') }}">
		<i class="fa fa-lightbulb u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('Tips') }}</span>
	</a>
</li>
<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="{{ url('live_matches') }}">
		<i class="fa fa-tv u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('Live Matches') }}</span>
	</a>
</li>

<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="{{ url('highlights') }}">
		<i class="fa fa-tv u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('Highlights') }}</span>
	</a>
</li>
<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="{{ url('subscriptions') }}">
		<i class="fa fa-boxes u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('Subscriptions') }}</span>
	</a>
</li>
<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="{{ url('notifications') }}">
		<i class="fa fa-bell u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('Notifications') }}</span>
	</a>
</li>
<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="{{ url('users') }}">
		<i class="fa fa-users u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('Manage Users') }}</span>
	</a>
</li>
<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="{{ url('cache') }}">
		<i class="fas fa-trash u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('Cache Clear') }}</span>
	</a>
</li>
<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="#!" data-target="#administration">
		<i class="far fa-folder-open u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('Administration') }}</span>
		<i class="fa fa-angle-right u-sidebar-nav-menu__item-arrow"></i>
		<span class="u-sidebar-nav-menu__indicator"></span>
	</a>

	<ul id="administration" class="u-sidebar-nav-menu u-sidebar-nav-menu--second-level" style="display: none;">
		<li class="u-sidebar-nav-menu__item">
			<a class="u-sidebar-nav-menu__link" href="{{ url('system_users') }}">
				<span class="u-sidebar-nav-menu__item-icon fa fa-angle-right"></span>
				<span class="u-sidebar-nav-menu__item-title">{{ _lang('Syatem Users') }}</span>
			</a>
		</li>
		<li class="u-sidebar-nav-menu__item">
			<a class="u-sidebar-nav-menu__link" href="{{ url('app_settings') }}">
				<span class="u-sidebar-nav-menu__item-icon fa fa-angle-right"></span>
				<span class="u-sidebar-nav-menu__item-title">{{ _lang('App Settings') }}</span>
			</a>
		</li>
		<li class="u-sidebar-nav-menu__item">
			<a class="u-sidebar-nav-menu__link" href="{{ url('general_settings') }}">
				<span class="u-sidebar-nav-menu__item-icon fa fa-angle-right"></span>
				<span class="u-sidebar-nav-menu__item-title">{{ _lang('General Settings') }}</span>
			</a>
		</li>
		
	</ul>
</li>
<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="#!" data-target="#prediction">
		<i class="fab fa-apple u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('Goat Betting App') }}</span>
		<i class="fa fa-angle-right u-sidebar-nav-menu__item-arrow"></i>
		<span class="u-sidebar-nav-menu__indicator"></span>
	</a>

	<ul id="prediction" class="u-sidebar-nav-menu u-sidebar-nav-menu--second-level" style="display: none;">
		<li class="u-sidebar-nav-menu__item">
			<a class="u-sidebar-nav-menu__link" href="{{ url('prediction_app_settings') }}">
				<span class="u-sidebar-nav-menu__item-icon fa fa-angle-right"></span>
				<span class="u-sidebar-nav-menu__item-title">{{ _lang('App Settings') }}</span>
			</a>
		</li>
		<li class="u-sidebar-nav-menu__item">
			<a class="u-sidebar-nav-menu__link" href="{{ url('general_settings') }}">
				<span class="u-sidebar-nav-menu__item-icon fa fa-angle-right"></span>
				<span class="u-sidebar-nav-menu__item-title">{{ _lang('General Settings') }}</span>
			</a>
		</li>
		<li class="u-sidebar-nav-menu__item">
			<a class="u-sidebar-nav-menu__link" href="{{ url('prediction_app_notifications') }}">
				<span class="u-sidebar-nav-menu__item-icon fa fa-angle-right"></span>
				<span class="u-sidebar-nav-menu__item-title">{{ _lang('Notifications') }}</span>
			</a>
		</li>
	</ul>
</li>
<li class="u-sidebar-nav-menu__item">
	<a class="u-sidebar-nav-menu__link" href="#!" data-target="#real">
		<i class="fab fa-apple u-sidebar-nav-menu__item-icon"></i>
		<span class="u-sidebar-nav-menu__item-title">{{ _lang('Real Prediction App') }}</span>
		<i class="fa fa-angle-right u-sidebar-nav-menu__item-arrow"></i>
		<span class="u-sidebar-nav-menu__indicator"></span>
	</a>

	<ul id="real" class="u-sidebar-nav-menu u-sidebar-nav-menu--second-level" style="display: none;">
		<li class="u-sidebar-nav-menu__item">
			<a class="u-sidebar-nav-menu__link" href="{{ url('real_app_settings') }}">
				<span class="u-sidebar-nav-menu__item-icon fa fa-angle-right"></span>
				<span class="u-sidebar-nav-menu__item-title">{{ _lang('App Settings') }}</span>
			</a>
		</li>
		<li class="u-sidebar-nav-menu__item">
			<a class="u-sidebar-nav-menu__link" href="{{ url('real_app_notifications') }}">
				<span class="u-sidebar-nav-menu__item-icon fa fa-angle-right"></span>
				<span class="u-sidebar-nav-menu__item-title">{{ _lang('Notifications') }}</span>
			</a>
		</li>
		<li class="u-sidebar-nav-menu__item">
			<a class="u-sidebar-nav-menu__link" href="{{ url('general_settings') }}">
				<span class="u-sidebar-nav-menu__item-icon fa fa-angle-right"></span>
				<span class="u-sidebar-nav-menu__item-title">{{ _lang('General Settings') }}</span>
			</a>
		</li>
	</ul>
</li>