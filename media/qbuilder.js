dojo.require("dijit.form.Button");
dojo.require("dojox.grid.DataGrid");
dojo.require("dojox.data.HtmlStore");
dojo.require("dojox.charting.Chart2D");
dojo.require("dojox.charting.themes.PlotKit.blue");
dojo.require("dojox.charting.themes.Distinctive");
dojo.require("dojox.charting.action2d.Tooltip");
dojo.require("dojox.charting.action2d.Magnify");
dojo.require("dojox.charting.widget.Legend");
dojo.require("dojox.layout.ResizeHandle");
dojo.require("dojox.widget.AnalogGauge");
dojo.require("dojox.widget.gauge.AnalogArcIndicator");
dojo.require("dojox.widget.gauge.AnalogArrowIndicator");
dojo.require("dojox.widget.gauge.AnalogNeedleIndicator");
dojo.require("dojox.widget.gauge.BarIndicator");

var _current_filter_id = 0;
var _current_grouping_id = 0;
var _current_extra_id = 0;
var DEBUG = true;

function clear_dom_element_from_dojo_widgets(element)
    {
    dojo.forEach(
        dojo.query('[widgetId]', element),
        function (widget)
            {
            widget = dijit.byId(dojo.attr(widget, 'widgetId'));
            if (widget)
                {
                widget.destroyRecursive();
                }
            });
    }

function get_filter_id()
    {
    filter_id = _current_filter_id;
    _current_filter_id ++;
    return filter_id;
    }
function get_grouping_id()
    {
    grouping_id = _current_grouping_id;
    _current_grouping_id ++;
    return grouping_id;
    }
function get_extra_id()
    {
    extra_id = _current_extra_id;
    _current_extra_id ++;
    return extra_id;
    }

function clear_dom_element(element_id)
    {
    if (!element_id) return;
    clear_dom_element_from_dojo_widgets(element_id);
    var node = dojo.byId(element_id);
    if (node)
        {
        while (node.hasChildNodes())
            {
            node.removeChild(node.lastChild);
            }
        }
    }

function clear_default_elements()
    {
    clear_dom_element('model_choose_div');
    clear_dom_element('filter_actions');
    clear_dom_element('active_filters');
    clear_dom_element('grouping_actions');
    clear_dom_element('active_groupings');
    clear_dom_element('display_type_action');
    clear_dom_element('active_display_type');
    clear_dom_element('chosen_query_div');
    clear_dom_element('resulting_query');
    clear_dom_element('resulting_data');
    clear_dom_element("active_extra_choices");
    clear_dom_element("extra_choices_actions");
    }

function select_whattodo(field)
    {
    var form = dojo.byId('qbuilder_form');
    var xhrArgs = {
        //~ url:field.action,
        url : '/qbuilder/whattodochoose',
        handleAs:"json",
        load: function(data)
            {
            clear_default_elements();
            _current_filter_id = 0;
            _current_grouping_id = 0;
            if (data.selectables)
                {
                var model_choose_div = dojo.byId('model_choose_div');
                dojo.create('span',{innerHTML:'des'},model_choose_div);
                var modelchoose = dojo.create("select", {id:'model',name:'model',onChange:'select_model(this);'}, model_choose_div);
                dojo.create("option", {value:0, innerHTML:''}, modelchoose);
                dojo.forEach(data.selectables, function(item)
                    {
                    dojo.create("option", {value:item[0], innerHTML:item[1]}, modelchoose);
                    });
                }
            if (data.display_types)
                {
                var display_types_menu = new dijit.Menu({});
                dojo.style(display_types_menu.domNode, "display", "none");
                dojo.style(display_types_menu.domNode, "width", "200px");
                dojo.forEach(data.display_types, function(display_type)
                    {
                    display_types_menu.addChild(new dijit.PopupMenuItem({
                        label: display_type[1],
                        onClick: function(mouse_event)
                            {
                            choose_display_type(display_type);
                            }
                        }));
                    });
                var display_types_button = new dijit.form.DropDownButton({
                    label : "Tableau",
                    name  : "display_type_choose",
                    id    : "display_type_choose",
                    dropDown : display_types_menu,
                    });
                dojo.byId('display_type_action').appendChild(display_types_button.domNode);
                dojo.style('display_type', 'display', 'inline');
                dojo.style('test_query_btn', 'display', 'inline');
                }
            else
                {
                dojo.style('display_type', 'display', 'none');
                }
            if (data.event_choices)
                {
                dojo.create('input', {
                    type: 'hidden',
                    id  : 'model',
                    name: 'model',
                    value:'Evenement',
                    },
                    'model_choose_div');
                var model_choose_div = dojo.byId('model_choose_div');
                var starting_event_div = dojo.create('div', {id:'starting_event_div'}, model_choose_div);
                var ending_event_div   = dojo.create('div', {id:'ending_event_div'}, model_choose_div);
                dojo.style(starting_event_div, 'display', 'inline');
                dojo.style(ending_event_div, 'display', 'inline');
                dojo.create('span',{innerHTML:'entre'},starting_event_div);
                var starting_events_menu = new dijit.Menu({});
                dojo.style(starting_events_menu.domNode, "display", "none");
                dojo.style(starting_events_menu.domNode, "width", "200px");
                dojo.forEach(data.event_choices, function(starting_event)
                    {
                    starting_events_menu.addChild(new dijit.PopupMenuItem({
                        label: starting_event[1],
                        onClick: function(mouse_event)
                            {
                            choose_starting_event(starting_event);
                            }
                        }));
                    });
                var starting_events_button = new dijit.form.DropDownButton({
                    label : "  ",
                    name  : "starting_event_choose",
                    id    : "starting_event_choose",
                    dropDown : starting_events_menu,
                    });
                starting_event_div.appendChild(starting_events_button.domNode);
                }
            if (data.extra_choices_possible)
                {
                var new_extra_choices_menu = new dijit.Menu({});
                dojo.style(new_extra_choices_menu.domNode, "display", "none");
                dojo.style(new_extra_choices_menu.domNode, "width", "200px");
                dojo.forEach(data.extra_choices_possible, function(possible_choice)
                    {
                    var this_submenu = new dijit.Menu({});
                    dojo.forEach(possible_choice.possibilities, function(possibility)
                        {
                        this_submenu.addChild(new dijit.PopupMenuItem({
                            label: possibility.label,
                            onClick: function(mouse_event)
                                {
                                add_extra_choice(possible_choice.code, possibility.code);
                                }
                            }));
                        });
                    new_extra_choices_menu.addChild(new dijit.PopupMenuItem({
                        label : possible_choice.label,
                        popup: this_submenu
                        }));
                    });
                var extra_choices_button = new dijit.form.DropDownButton({
                    label : "Options complémentaires",
                    name  : "extra_choices_choose",
                    id    : "extra_choices_choose",
                    dropDown : new_extra_choices_menu,
                    });
                dojo.byId('extra_choices_actions').appendChild(extra_choices_button.domNode);
                }
            if (data.query_choices)
                {
                var model_choose_div = dojo.byId('model_choose_div');
                var query_choice_div = dojo.create('div', {id:'starting_event_div'}, model_choose_div);
                dojo.style(query_choice_div, 'display', 'inline');
                dojo.create('span',{innerHTML:'portant le nom'},query_choice_div);
                var query_choice_menu = new dijit.Menu({});
                dojo.style(query_choice_menu.domNode, "display", "none");
                dojo.style(query_choice_menu.domNode, "width", "200px");
                dojo.forEach(data.query_choices, function(query)
                    {
                    query_choice_menu.addChild(new dijit.PopupMenuItem({
                        label: query[1],
                        onClick: function(mouse_event)
                            {
                            choose_query(query);
                            }
                        }));
                    });
                var starting_events_button = new dijit.form.DropDownButton({
                    label : "  ",
                    name  : "query_choose",
                    id    : "query_choose",
                    dropDown : query_choice_menu,
                    });
                query_choice_div.appendChild(starting_events_button.domNode);
                }
            if (DEBUG) console.debug("ok", data);
            },
        error: function(error)
            {
            if (DEBUG) console.error("ko",error);
            },
        postData: "requete=" + encodeURIComponent(dojo.formToJson(form)),
        };
    dojo.xhrPost(xhrArgs);
    }

function select_model(field)
    {
    var form = dojo.byId('qbuilder_form');
    var xhrArgs = {
        url : 'modelchoose',
        handleAs:"json",
        load: function(data)
            {
            clear_dom_element('filter_actions');
            clear_dom_element('active_filters');
            _current_filter_id = 0;
            clear_dom_element('grouping_actions');
            clear_dom_element('active_groupings');
            _current_grouping_id = 0;
            var new_group_menu = new dijit.Menu({});
            dojo.style(new_group_menu.domNode, "display", "none");
            dojo.style(new_group_menu.domNode, "width", "200px");
            dojo.forEach(data.possible_group_by, function(grouping_model)
                {
                var this_submenu = new dijit.Menu({});
                dojo.forEach(grouping_model.fields, function(grouping_field)
                    {
                    this_submenu.addChild(new dijit.PopupMenuItem({
                        label: grouping_field.field[0],
                        onClick: function(mouse_event)
                            {
                            add_grouping(grouping_model.model_name, grouping_model.title, grouping_field.title, grouping_field.field);
                            }
                        }));
                    });
                new_group_menu.addChild(new dijit.PopupMenuItem({label : grouping_model.title, popup: this_submenu}));
                });
            var group_button = new dijit.form.DropDownButton({
                label : "regroupés par",
                name  : "group_by_choose",
                id    : "group_by_choose",
                dropDown : new_group_menu,
                });
            dojo.byId('grouping_actions').appendChild(group_button.domNode);
            var new_filter_menu = new dijit.Menu({});
            dojo.style(new_filter_menu.domNode, "display", "none");
            dojo.style(new_filter_menu.domNode, "width", "200px");
            dojo.forEach(data.possible_filters, function(possible_filter)
                {
                var this_submenu = new dijit.Menu({});
                dojo.forEach(possible_filter.filters, function(field_filter)
                    {
                    var this_subsubmenu = new dijit.Menu({});
                    dojo.forEach(field_filter.possible_types, function(filter_type)
                        {
                        this_subsubmenu.addChild(new dijit.PopupMenuItem({
                            label:filter_type[1],
                            onClick: function(mouse_event)
                                {
                                add_filter(possible_filter.model_name, field_filter.field_name, filter_type[0]);
                                }
                            }));
                        });
                    this_submenu.addChild(new dijit.PopupMenuItem({label:field_filter.field_name, popup:this_subsubmenu}));
                    });
                new_filter_menu.addChild(new dijit.PopupMenuItem({label :possible_filter.title, popup:this_submenu}));
                });
            var plus_button = new dijit.form.DropDownButton({
                label : "Ajouter un filtre",
                name  : "filter_add",
                id    : "filter_add",
                dropDown: new_filter_menu,
                });
            dojo.byId('filter_actions').appendChild(plus_button.domNode);
            if (DEBUG) console.debug("ok", data);
            },
        error: function(error)
            {
            if (DEBUG) console.error("ko",error);
            },
        postData: "requete=" + encodeURIComponent(dojo.formToJson(form)),
        };
    dojo.xhrPost(xhrArgs);
    }

function add_filter(filtering_model, filtering_field, filtering_type)
    {
    var form = dojo.byId('qbuilder_form');
    var postData = dojo.toJson({
        'model' : form.model.value,
        'filtering_model' : filtering_model,
        'filtering_field' : filtering_field,
        'filtering_type' : filtering_type,
        'filter_id' : get_filter_id(),
        });
    var xhrArgs = {
        url : 'filteradd',
        handleAs:"json",
        load: function(data)
            {
            var active_filters = dojo.byId('active_filters');
            var new_filter = dojo.create("div", {
                filtering_model: filtering_model,
                filtering_field: filtering_field,
                filtering_type : filtering_type,
                innerHTML : data.filter_html,
                }, active_filters);
            dojo.parser.parse(new_filter);
            if (DEBUG) console.debug("ok", data);
            },
        error: function(error)
            {
            if (DEBUG) console.error("ko",error);
            },
        postData: "requete=" + encodeURIComponent(postData),
        };
    dojo.xhrPost(xhrArgs);    
    }

function add_a_value_for_filter(filter_id)
    {
    dojo.create("input",{type:'text', name:'value_for_filter_' + filter_id + '[]', size:2},'values_for_filter_' + filter_id);
    }

function remove_filter(filter_id)
    {
    remove('filter_' + filter_id);
    //~ var filter_to_remove = dojo.byId('filter_' + filter_id);
    //~ filter_to_remove.parentNode.removeChild(filter_to_remove);
    }

function generate_piechart(layout, parent_id, pk)
    {
    dojo.create("div", {id: 'piechart-' + pk,style:'width: 500px; height: 500px;'}, dojo.byId(parent_id));
    var piechart = new dojox.charting.Chart2D("piechart-"+pk).
        setTheme(dojox.charting.themes.PlotKit.blue).
        addPlot("default", layout.piestyle);
    dojo.forEach(layout.series, function(serie)
        {
        piechart.addSeries(serie.title, serie.data);
        });
    piechart.render();
    if (layout.resize) piechart.resize(layout.resize.width, layout.resize.height);
    }

function generate_barchart(layout, parent_id, pk, resizeable)
    {
    dojo.create("table", {id: 'barchart_table-'+pk, style:'background-color: white; width: 0;', class:'grid-cells'}, dojo.byId(parent_id));
    var le_tr = dojo.create("tr",{}, dojo.byId('barchart_table-'+pk));
    var height = (layout.resize ? layout.resize.height : '500');
    var width  = (layout.resize ? layout.resize.width  : '500');
    dojo.create("td", {id: 'barchart-'+pk, style:'height: ' + height + 'px; width: ' + width + 'px;'}, le_tr);
    if (!layout.hide_legend)
        {
        dojo.create("div", {id: 'legend_barchart-'+pk}, dojo.create("td", {style:'background-color: white;'}, le_tr));
        }
    var barchart = new dojox.charting.Chart2D('barchart-'+pk).
        setTheme(dojox.charting.themes.Distinctive).
        addAxis("y", {vertical: true, fixLower: "major", fixUpper: "major"}).
        addAxis("x", {majorLabels: true, minorLabels: true, includeZero: true, minorTicks: false, microTicks: false, majorTickStep: 1,
            labels: layout.x_labels}).
        addPlot("default", {type: "ClusteredColumns", gap: 10});
    dojo.forEach(layout.series, function(serie)
        {
        barchart.addSeries(serie.title, serie.data);//, serie.styling);
        });
    var anim_tooltip_barchart = new dojox.charting.action2d.Tooltip(barchart, "default");
    barchart.render();
    if (layout.resize) barchart.resize(layout.resize.width, layout.resize.height);
    //~ barchart.resize(300,200);
    if (!layout.hide_legend)
        {
        var legend_barchart = new dojox.charting.widget.Legend({chart: barchart, horizontal: false}, "legend_barchart-"+pk);
        }
    //~ if (resizeable)
        //~ {
        //~ var rhandle = dojo.create('div',{style:'position: relative;', id:'resizehandle'}, dojo.byId('barchart-'+pk));
        //~ var resizer = new dojox.layout.ResizeHandle({
            //~ targetId : 'barchart-'  + pk,
            //~ activeResize: true,
            //~ }, rhandle);
        //~ resizer.startup();
        //~ dojo.style(rhandle, 'position', 'relative');
        //~ }
    }

function generate_linechart(layout, parent_id, pk)
    {
    var my_label_func = function(item, store)
        {
        var myDate = new Date(item * 1000);
        return dojo.date.locale.format(myDate, layout.date_formatting);
        };
    dojo.create("table", {id: 'linechart_table-'+pk, style:'background-color: white;', class:'grid-cells'}, dojo.byId(parent_id));
    var le_tr = dojo.create("tr",{}, dojo.byId('linechart_table-'+pk));
    var height = (layout.resize ? layout.resize.height : '500');
    var width  = (layout.resize ? layout.resize.width  : '500');
    dojo.create("td", {id: 'linechart-'+pk, style:'height: ' + height + 'px; width: ' + width + 'px;'}, le_tr);
    if (!layout.hide_legend)
        {
        dojo.create("div", {id: 'legend_linechart-'+pk}, dojo.create("td", {style:'background-color: white;'}, le_tr));
        }
    var linechart = new dojox.charting.Chart2D('linechart-'+pk).
        setTheme(dojox.charting.themes.Distinctive).
        addAxis("y", {vertical: true, fixLower: "major", fixUpper: "major"}).
        addAxis("x", {fixLower: "major", fixUpper:"major"}).//, labelFunc: my_label_func}).
        addPlot("default", {type: "Default", lines: true, markers: true, tension: 0});
    dojo.forEach(layout.series, function(serie)
        {
        linechart.addSeries(serie.title, serie.data);
        });
    var anim1a = new dojox.charting.action2d.Magnify(linechart, "default");
    var anim1b = new dojox.charting.action2d.Tooltip(linechart, "default");
    linechart.render();
    if (layout.resize) linechart.resize(layout.resize.width, layout.resize.height);
    if (!layout.hide_legend)
        {
        var legend1 = new dojox.charting.widget.Legend({chart: linechart, horizontal: false}, "legend_linechart-"+pk);
        }
    }

function generate_gauge(layout, parent_id, pk)
    {
    dojo.create("table", {id: 'gauge_table-'+pk, style:'background-color: white;', class:'grid-cells'}, dojo.byId(parent_id));
    var le_tr = dojo.create("tr",{}, dojo.byId('gauge_table-'+pk));
    var height = (layout.resize ? layout.resize.height : '500');
    dojo.create("td", {id: 'gauge-'+pk, style:'height: ' + height + 'px;'}, le_tr);
    if (!layout.hide_legend)
        {
        dojo.create("div", {id: 'legend_gauge-'+pk}, dojo.create("td", {style:'background-color: white;'}, le_tr));
        }
    // Used for a gradient arc indicator below:
    //~ var fill = {
        //~ 'type': 'linear',
        //~ 'x1': 50,
        //~ 'y1': 50,
        //~ 'x2': 550,
        //~ 'y2': 550,
        //~ 'colors': [{offset: 0, color: 'black'}, {offset: 0.5, color: 'black'}, {offset: 0.75, color: 'yellow'}, {offset: 1, color: 'red'}]
        //~ };
    var indicators = [];
    dojo.forEach(layout.indicators, function(indic)
        {
        indicators.push(new dojox.widget.gauge.AnalogArrowIndicator({
            value : indic.value,
            width: indic.width,
            noChange: true,
            hideValue: true,
            length: indic.length,
            hover: indic.tooltip,
            title: indic.title,
            color: indic.color,
            }));
        });
    layout.gauge.indicators = indicators;
    var gauge = new dojox.widget.AnalogGauge(layout.gauge, 'gauge-'+pk);
    //~ dojo.forEach(layout.series, function(serie)
        //~ {
        //~ gauge.addSeries(serie.title, serie.data);
        //~ });
    //~ var anim1a = new dojox.charting.action2d.Magnify(gauge, "default");
    //~ var anim1b = new dojox.charting.action2d.Tooltip(gauge, "default");
    gauge.startup();
    //~ if (layout.resize) gauge.resize(layout.resize.width, layout.resize.height);
    //~ if (!layout.hide_legend)
        //~ {
        //~ var legend1 = new dojox.charting.widget.Legend({chart: gauge, horizontal: false}, "legend_gauge-"+pk);
        //~ }
    return gauge;
    }

function generate_table(layout, parent_id, pk)
    {
    if (DEBUG) console.debug(layout, parent_id, pk);
    var returnedData = new dojox.data.HtmlStore({
        dataId : pk == 0 ? 'resultingDataTable' : 'resultingDataTable-' + pk,
        id: 'totoatat',
        });
    if (DEBUG) console.debug(returnedData);
    dojo.forEach(layout.structure, function(line)
        {
        if (line.coloring)
            {
            line.formatter = function(val, rowIdx, cell)
                {
                console.debug("line",line, val, rowIdx, cell);
                var store = cell.grid.store;
                var data_line = store.fetch({query : {index: rowIdx}, onItem: function (item, request)
                    {
                    var classes = store.getValue(item, '_classes_', '');
                    if (classes != '')
                        {
                        cell.customClasses.push(classes);
                        }
                    console.debug("fetched item", item, store.getValue(item, 'color','black'));
                    }});
                //~ console.debug(cell.grid.store);
                //~ if (line.classes)
                    //~ {
                    //~ 
                    //~ }
                return val;
                };
            }
        });
    var grid = new dojox.grid.DataGrid({
        id:'myDataGrid-' + pk,
        query : {},
        store: returnedData,
        clientSort: true,
        //~ columnReordering: true,
        rowSelector: '20px',
        structure: layout.structure,
        autoHeight: 20,
        },
        dojo.create('div', {}, parent_id));
    grid.startup();
    }

function test_query()
    {
    var form = dojo.byId('qbuilder_form');
    clear_dom_element('resulting_query');
    clear_dom_element('resulting_data');
    var xhrArgs = {
        url : 'test_query',
        handleAs : 'json',
        load: function(data)
            {
            if (data.sql)
                {
                dojo.byId('resulting_query').innerHTML = data.sql;
                }
            if (data.data)
                {
                var resulting_data_table = dojo.create("table",{},dojo.byId('resulting_data'));
                resulting_data_table.innerHTML = data.data;
                if (data.grid_layout)
                    {
                    generate_table(data.grid_layout, 'resulting_data', 0);
                    }
                if (data.pie_layout)
                    {
                    generate_piechart(data.pie_layout, 'resulting_data', 0);
                    }
                if (data.bar_layout)
                    {
                    generate_barchart(data.bar_layout, 'resulting_data', 0);
                    }
                if (data.line_layout)
                    {
                    generate_linechart(data.line_layout, 'resulting_data', 0);
                    }
                if (data.gauge_layout)
                    {
                    generate_gauge(data.gauge_layout, 'resulting_data', 0);
                    }
                }
            if (DEBUG) console.debug("ok",data);
            },
        error: function(error)
            {
            if (DEBUG) console.error("ko",error);
            },
        postData: "requete=" + encodeURIComponent(dojo.formToJson(form)),
        };
    dojo.xhrPost(xhrArgs);
    }

function add_grouping(model_name, model_title, field_title, field)
    {
    var form = dojo.byId('qbuilder_form');
    var postData = dojo.toJson({
        'model' : form.model.value,
        'grouping_model' : model_name,
        'grouping_field' : field_title,
        'grouping_id' : get_grouping_id(),
        });
    var xhrArgs = {
        url : 'groupingadd',
        handleAs:"json",
        load: function(data)
            {
            var active_groupings = dojo.byId('active_groupings');
            var new_grouping = dojo.create("div", {
                model_title: model_title,
                field_title: field_title,
                innerHTML : data.grouping_html,
                }, active_groupings);
            dojo.parser.parse(active_groupings);
            if (DEBUG) console.debug("ok", data);
            },
        error: function(error)
            {
            if (DEBUG) console.error("ko",error);
            },
        postData: "requete=" + encodeURIComponent(postData),
        };
    dojo.xhrPost(xhrArgs);    
    }
function remove_grouping(grouping_id)
    {
    remove('grouping_' + grouping_id);
    //~ var grouping_to_remove = dojo.byId('grouping_' + grouping_id);
    //~ grouping_to_remove.parentNode.removeChild(grouping_to_remove);
    }

function choose_display_type(display_type)
    {
    clear_dom_element('active_display_type');
    dojo.create('input', {
        type: 'hidden',
        readonly:'readonly',
        name:'display_type_choice',
        id:'display_type_choice',
        value:display_type[0],
        }, dojo.byId('active_display_type'));
    var display_type_choose = dijit.byId('display_type_choose');
    if (display_type_choose)
        {
        display_type_choose.attr('label', display_type[1]);
        }
    }

function choose_starting_event(event)
    {
    clear_dom_element('ending_event_div');
    var form = dojo.byId('qbuilder_form');
    var starting_event_choose = dijit.byId('starting_event_choose');
    if (starting_event_choose)
        {
        starting_event_choose.attr('label', event[1]);
        }
    var starting_event_choice = dojo.byId('starting_event_choice');
    if (starting_event_choice)
        {
        dojo.attr(starting_event_choice, 'value', event[0]);
        }
    else
        {
        dojo.create('input', {
            type: 'hidden',
            readonly:'readonly',
            name:'starting_event_choice',
            id:'starting_event_choice',
            value:event[0],
            }, dojo.byId('starting_event_div'));
        }
    var xhrArgs = {
        url : 'starting_event_choose',
        handleAs:"json",
        load: function(data)
            {
            var ending_event_div = dojo.byId('ending_event_div');
            dojo.create('span',{innerHTML:'et'},ending_event_div);
            var ending_events_menu = new dijit.Menu({});
            dojo.style(ending_events_menu.domNode, "display", "none");
            dojo.style(ending_events_menu.domNode, "width", "200px");
            dojo.forEach(data.event_choices, function(ending_event)
                {
                ending_events_menu.addChild(new dijit.PopupMenuItem({
                    label: ending_event[1],
                    onClick: function(mouse_event)
                        {
                        choose_ending_event(ending_event);
                        }
                    }));
                });
            var ending_events_button = new dijit.form.DropDownButton({
                label : "  ",
                name  : "ending_event_choose",
                id    : "ending_event_choose",
                dropDown : ending_events_menu,
                });
            dojo.byId('ending_event_div').appendChild(ending_events_button.domNode);
            if (DEBUG) console.debug("ok", data);
            },
        error: function(error)
            {
            if (DEBUG) console.error("ko",error);
            },
        postData: "requete=" + encodeURIComponent(dojo.formToJson(form)),
        };
    dojo.xhrPost(xhrArgs);
    }


function choose_ending_event(event)
    {
    var form = dojo.byId('qbuilder_form');
    var ending_event_choose = dijit.byId('ending_event_choose');
    if (ending_event_choose)
        {
        ending_event_choose.attr('label', event[1]);
        }
    var ending_event_choice = dojo.byId('ending_event_choice');
    if (ending_event_choice)
        {
        dojo.attr(ending_event_choice, 'value', event[0]);
        }
    else
        {
        dojo.create('input', {
            type: 'hidden',
            readonly:'readonly',
            name:'ending_event_choice',
            id:'ending_event_choice',
            value:event[0],
            }, dojo.byId('ending_event_div'));
        }
    var xhrArgs = {
        url : 'ending_event_choose',
        handleAs:"json",
        load: function(data)
            {
            clear_dom_element('filter_actions');
            clear_dom_element('active_filters');
            _current_filter_id = 0;
            clear_dom_element('grouping_actions');
            clear_dom_element('active_groupings');
            _current_grouping_id = 0;
            clear_dom_element('extra_choices_actions');
            clear_dom_element('active_extra_choices');
            var new_group_menu = new dijit.Menu({});
            dojo.style(new_group_menu.domNode, "display", "none");
            dojo.style(new_group_menu.domNode, "width", "200px");
            dojo.forEach(data.possible_group_by, function(grouping_model)
                {
                var this_submenu = new dijit.Menu({});
                dojo.forEach(grouping_model.fields, function(grouping_field)
                    {
                    this_submenu.addChild(new dijit.PopupMenuItem({
                        label: grouping_field.field[0],
                        onClick: function(mouse_event)
                            {
                            add_grouping(grouping_model.model_name, grouping_model.title, grouping_field.title, grouping_field.field);
                            }
                        }));
                    });
                new_group_menu.addChild(new dijit.PopupMenuItem({label : grouping_model.title, popup: this_submenu}));
                });
            var group_button = new dijit.form.DropDownButton({
                label : "regroupés par",
                name  : "group_by_choose",
                id    : "group_by_choose",
                dropDown : new_group_menu,
                });
            dojo.byId('grouping_actions').appendChild(group_button.domNode);
            var new_filter_menu = new dijit.Menu({});
            dojo.style(new_filter_menu.domNode, "display", "none");
            dojo.style(new_filter_menu.domNode, "width", "200px");
            dojo.forEach(data.possible_filters, function(possible_filter)
                {
                var this_submenu = new dijit.Menu({});
                dojo.forEach(possible_filter.filters, function(field_filter)
                    {
                    var this_subsubmenu = new dijit.Menu({});
                    dojo.forEach(field_filter.possible_types, function(filter_type)
                        {
                        this_subsubmenu.addChild(new dijit.PopupMenuItem({
                            label:filter_type[1],
                            onClick: function(mouse_event)
                                {
                                add_filter(possible_filter.model_name, field_filter.field_name, filter_type[0]);
                                }
                            }));
                        });
                    this_submenu.addChild(new dijit.PopupMenuItem({label:field_filter.field_name, popup:this_subsubmenu}));
                    });
                new_filter_menu.addChild(new dijit.PopupMenuItem({label :possible_filter.title, popup:this_submenu}));
                });
            var plus_button = new dijit.form.DropDownButton({
                label : "Ajouter un filtre",
                name  : "filter_add",
                id    : "filter_add",
                dropDown: new_filter_menu,
                });
            dojo.byId('filter_actions').appendChild(plus_button.domNode);
            if (DEBUG) console.debug("ok", data);
            },
        error: function(error)
            {
            if (DEBUG) console.error("ko",error);
            },
        postData: "requete=" + encodeURIComponent(dojo.formToJson(form)),
        };
    dojo.xhrPost(xhrArgs);
    }

function save_query()
    {
    var form = dojo.byId('qbuilder_form');
    var name = prompt("Saisir un nom pour la requête");
    var postData = dojo.fromJson(dojo.formToJson(form));
    postData['name'] = name;
    var xhrArgs = {
        url : 'save_query',
        handleAs : 'json',
        load : function(data)
            {
            if (data.created)
                {
                alert("Requête " + data.name + " sauvegardée sous le numéro " + data.pk);
                }
            else
                {
                alert("Erreur à la sauvegarde de la requête " + data.name + " : " + data.error);
                }
            },
        postData: "requete=" + encodeURIComponent(dojo.toJson(postData)),
        };
    dojo.xhrPost(xhrArgs);
    }

function choose_query(query)
    {
    clear_dom_element('chosen_query_div');
    dojo.create('input', {
        type: 'text',
        readonly:'readonly',
        name:'chosen_query',
        id:'chosen_query',
        value:query[0],
        }, dojo.byId('chosen_query_div'));
    var query_choose = dijit.byId('query_choose');
    if (query_choose)
        {
        query_choose.attr('label', query[1]);
        }
    }

function add_extra_choice(extra_type, extra_choice)
    {
    /*
    Si ce extra_choice existe déjà, on s'arrête tout de suite.
    */
    if (!dojo.query(".extra_choice_div", dojo.byId("active_extra_choices")).every(function(extra_div)
        {
        if ((dojo.attr(extra_div, "extra_type") == extra_type) && (dojo.attr(extra_div, "extra_choice") == extra_choice))
            {
            return false;
            }
        return true;
        }))
        {
        return;
        }
    /*
    On y va
    */
    var extra_id = get_extra_id();
    var form = dojo.byId('qbuilder_form');
    var postData = dojo.fromJson(dojo.formToJson(form));
    postData['extra_type'] = extra_type;
    postData['extra_choice'] = extra_choice;
    postData['extra_id'] = extra_id;
    var xhrArgs = {
        url : 'extrachoiceadd',
        handleAs:"json",
        load: function(data)
            {
            var active_extra_choices = dojo.byId('active_extra_choices');
            var new_extra = dojo.create("div", {
                id: 'extra_' + extra_id,
                extra_type: extra_type,
                extra_choice: extra_choice,
                class: 'extra_choice_div',
                innerHTML : data.extra_choice_html,
                }, active_extra_choices);
            dojo.parser.parse(new_extra);
            if (DEBUG) console.debug("ok", data);
            },
        error: function(error)
            {
            if (DEBUG) console.error("ko",error);
            },
        postData: "requete=" + encodeURIComponent(dojo.toJson(postData)),
        };
    dojo.xhrPost(xhrArgs);    
    }

function remove(id)
    {
    var to_remove = dojo.byId(id);
    if (to_remove)
        {
        to_remove.parentNode.removeChild(to_remove);
        }
    }

