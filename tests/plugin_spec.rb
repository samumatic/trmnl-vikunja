# frozen_string_literal: true

# This plugin's tests, run with `bin/trmnlp test` (add `--report report` for a page of every screen it drew).
# Docs: https://github.com/usetrmnl/trmnlp#testing-plugins
# Fixtures are a made-up Vikunja (no personal data); the clock is Wednesday 2026-11-11, 11:00 in Berlin.
RSpec.describe 'Vikunja Tasks' do
  def fixture(name) = JSON.parse(File.read(File.join(__dir__, 'fixtures', name)))

  let(:now) { Time.utc(2026, 11, 11, 10) }
  # The open and the done-today request differ only in their filter.
  OPEN = 'https://tasks.example.com/api/v1/tasks?*filter=done+%3D+false*'
  DONE = 'https://tasks.example.com/api/v1/tasks?*filter=done+%3D+true*'
  let(:mocks) do
    { OPEN => { json: fixture('tasks.json') }, DONE => { json: fixture('done-today.json') },
      'https://tasks.example.com/api/v1/projects*' => { json: fixture('projects.json') } }
  end
  let(:custom_fields) do
    { 'base_url' => 'https://tasks.example.com', 'api_token' => 'tk_test', 'language' => 'en' }
  end
  let(:variables) { { 'trmnl' => { 'user' => { 'time_zone_iana' => 'Europe/Berlin', 'locale' => 'en' } } } }

  # Every view on TRMNL's devices, a failing API and every select option, checked for page errors and leaked values.
  it_behaves_like 'a publishable recipe'

  def vk(fields = {})
    trmnl.transform(now:, mocks:, variables:, custom_fields: custom_fields.merge(fields)).data['vk']
  end

  def titles(result) = result['groups'].flat_map { |g| g['tasks'].map { it['title'] } }

  describe 'the request' do
    let(:requests) { trmnl.transform(now:, mocks:, variables:, custom_fields:).requests }

    it 'asks for open tasks, the project names and what was done today, with the token' do
      expect(requests.map { it[:url] }).to contain_exactly(
        'https://tasks.example.com/api/v1/tasks?per_page=250&filter=done+%3D+false&filter_timezone=Europe%2FBerlin',
        'https://tasks.example.com/api/v1/projects?per_page=250',
        'https://tasks.example.com/api/v1/tasks?per_page=250&filter=done+%3D+true+%26%26+done_at+%3E%3D+now%2Fd&filter_timezone=Europe%2FBerlin'
      )
      expect(requests.first[:headers]).to include('authorization' => 'Bearer tk_test')
    end

    it 'adds the extra filter in brackets and drops a trailing slash from the address' do
      fields = custom_fields.merge('filter' => 'priority >= 3', 'base_url' => 'https://tasks.example.com/')
      url = trmnl.transform(now:, mocks:, variables:, custom_fields: fields).requests.first[:url]
      expect(url).to start_with('https://tasks.example.com/api/v1/tasks?')
      expect(url).to include('filter=done+%3D+false+%26%26+%28priority+%3E%3D+3%29')
    end

    it 'asks only for what is due by tomorrow in focus mode' do
      url = trmnl.transform(now:, mocks:, variables:, custom_fields: custom_fields.merge('mode' => 'focus')).requests.first[:url]
      expect(url).to include('filter=done+%3D+false+%26%26+due_date+%3C+now%2Fd%2B2d&')
    end

    it 'skips the done-today request when switched off' do
      fields = custom_fields.merge('show_done_today' => 'false')
      expect(trmnl.transform(now:, mocks:, variables:, custom_fields: fields).requests.size).to eq(2)
    end
  end

  describe 'the list' do
    it 'puts the most pressing first and groups by project' do
      result = vk
      expect(result['state']).to eq('ok')
      expect(result['instance']).to eq('9 open · 2 done')
      expect(result['groups'].map { it['name'] }).to eq(['Home', 'Groceries', 'Garden', 'Done today'])
      expect(titles(result)).to eq(['Take out the glass', 'Test smoke alarms', 'Bleed the radiators', 'Renew passport',
                                    'Bread', 'Drain cleaner', 'Oat milk', 'Apples', 'Cover the roses for winter',
                                    'Empty the dishwasher', 'Coffee'])
    end

    it 'says when tasks are due in plain words' do
      due = vk('group_by_project' => 'false')['groups'].first['tasks'].to_h { [it['title'], [it['due'], it['urgency']]] }
      expect(due).to include('Take out the glass' => ['2 days late', 2], 'Bread' => ['Today 18:00', 1],
                             'Test smoke alarms' => ['Tomorrow', 0], 'Bleed the radiators' => ['Sat', 0],
                             'Cover the roses for winter' => ['Nov 30', 0], 'Renew passport' => ['Feb 15 2027', 0],
                             'Apples' => ['', 0])
    end

    it 'marks priority 3 to 5 with one to three !' do
      prio = vk['groups'].flat_map { it['tasks'] }.to_h { [it['title'], it['prio']] }
      expect(prio.values_at('Drain cleaner', 'Cover the roses for winter', 'Test smoke alarms', 'Apples'))
        .to eq(['!', '!!', '!!!', ''])
    end

    it 'speaks German' do
      result = vk('language' => 'de', 'group_by_project' => 'false')
      due = result['groups'].first['tasks'].to_h { [it['title'], it['due']] }
      expect(result['instance']).to eq('9 offen · 2 erledigt')
      expect(due.values_at('Take out the glass', 'Bread', 'Test smoke alarms', 'Bleed the radiators',
                           'Cover the roses for winter'))
        .to eq(['seit 2 Tagen', 'Heute 18:00', 'Morgen', 'Sa', '30. Nov.'])
    end

    it 'sorts by priority, title or age' do
      expect(titles(vk('sort' => 'priority', 'group_by_project' => 'false')).first(3))
        .to eq(['Test smoke alarms', 'Cover the roses for winter', 'Drain cleaner'])
      expect(titles(vk('sort' => 'title', 'group_by_project' => 'false')).first(2)).to eq(%w[Apples Bleed\ the\ radiators])
      expect(titles(vk('sort' => 'created', 'group_by_project' => 'false')).first(2)).to eq(['Oat milk', 'Bread'])
    end

    it 'shows the task labels unless switched off' do
      expect(vk['groups'].flat_map { it['tasks'] }.find { it['title'] == 'Drain cleaner' }['labels']).to eq(['Drugstore'])
      expect(vk('show_labels' => 'false')['groups'].flat_map { it['tasks'] }.flat_map { it['labels'] }).to be_empty
    end

    it 'never shows the HTML description' do
      screen = trmnl.render(view: 'full', device: 'og_plus', now:, mocks:, variables:, custom_fields:)
      expect(screen.text).not_to include('notes')
    end
  end

  describe 'assignees' do
    it 'shows who a task is assigned to, by first name or username' do
      people = vk['groups'].flat_map { it['tasks'] }.to_h { [it['title'], it['people']] }
      expect(people.values_at('Bread', 'Test smoke alarms', 'Apples')).to eq([%w[Alex], %w[Alex sam], []])
      screen = trmnl.render(view: 'full', device: 'og_plus', now:, mocks:, variables:, custom_fields:)
      expect(screen.text).to include('Alex', 'sam')
    end

    it 'hides them when switched off' do
      expect(vk('show_assignees' => 'false')['groups'].flat_map { it['tasks'] }.flat_map { it['people'] }).to be_empty
    end
  end

  describe 'focus mode' do
    it 'keeps only what is late or due today or tomorrow' do
      result = vk('mode' => 'focus', 'group_by_project' => 'false', 'show_done_today' => 'false')
      expect(titles(result)).to eq(['Take out the glass', 'Bread', 'Test smoke alarms'])
      expect(result['instance']).to eq('3 open')
    end

    it 'says so when nothing is due' do
      screen = trmnl.render(view: 'full', device: 'og_plus', now:, variables:,
                            custom_fields: custom_fields.merge('mode' => 'focus'),
                            mocks: mocks.merge(OPEN => { json: [] }, DONE => { json: [] }))
      expect(screen.text).to include('All done', 'Nothing due by tomorrow.')
    end
  end

  describe 'done today' do
    it 'lists what was ticked off today, newest first, ticked and without due date or priority' do
      done = vk['groups'].last
      expect(done['name']).to eq('Done today')
      expect(done['tasks'].map { it['title'] }).to eq(['Empty the dishwasher', 'Coffee'])
      expect(done['tasks'].map { it.values_at('done', 'prio', 'due', 'labels') }.uniq).to eq([[true, '', '', []]])
      expect(done['tasks'].first['people']).to eq(%w[sam])
    end

    it 'leaves out what was done yesterday' do
      expect(titles(vk)).not_to include('Water the plants')
    end

    it 'strikes them through on screen' do
      screen = trmnl.render(view: 'full', device: 'og_plus', now:, mocks:, variables:, custom_fields:)
      expect(screen.html).to include('vk-done')
      expect(screen.text).to include('Done today', 'Coffee')
    end

    it 'shows only open tasks when switched off' do
      result = vk('show_done_today' => 'false')
      expect(result['instance']).to eq('9 open')
      expect(result['groups'].map { it['name'] }).not_to include('Done today')
    end
  end

  describe 'choosing projects' do
    it 'takes names and IDs, and names the one project in the title' do
      result = vk('projects' => 'groceries')
      expect(result['title']).to eq('Groceries')
      expect(result['groups'].map { it['name'] }).to eq(['', 'Done today'])
      expect(titles(vk('projects' => '4, 5')).size).to eq(6)
    end

    it 'prefers its own title' do
      expect(vk('projects' => '3', 'title' => 'Shopping')['title']).to eq('Shopping')
    end

    it 'says which project it cannot find' do
      result = vk('projects' => 'Shoping')
      expect(result['state']).to eq('missing')
      expect(result['message']['text']).to include('Shoping')
    end
  end

  describe 'without a list to show' do
    it 'shows sample tasks without a token' do
      result = vk('api_token' => '')
      expect(result['state']).to eq('demo')
      expect(result['instance']).to eq('Sample')
      expect(titles(result)).to include('Oat milk')
    end

    it 'is all done when nothing is open' do
      screen = trmnl.render(view: 'full', device: 'og_plus', now:, variables:, custom_fields:,
                            mocks: mocks.merge(OPEN => { json: [] }, DONE => { json: [] }))
      expect(screen).to have_no_problems
      expect(screen.text).to include('All done')
    end

    it 'explains a rejected token' do
      rejected = { status: 401, json: { 'code' => 11, 'message' => 'missing, malformed, expired or otherwise invalid token provided' } }
      screen = trmnl.render(view: 'full', device: 'og_plus', now:, variables:, custom_fields:,
                            mocks: { 'https://tasks.example.com/*' => rejected })
      expect(screen).to have_no_problems
      expect(screen.text).to include('Token rejected')
    end

    it 'names the server it cannot reach' do
      screen = trmnl.render(view: 'full', device: 'og_plus', now:, variables:, custom_fields:,
                            mocks: { 'https://tasks.example.com/*' => { error: :reset } })
      expect(screen.text).to include('Vikunja unreachable', 'tasks.example.com')
    end
  end

  it 'fits a long list into every view, with the rest counted' do
    many = mocks.merge(OPEN => { json: fixture('many-tasks.json') })
    %w[full half_horizontal half_vertical quadrant].each do |view|
      %w[og_plus v2].each do |device|
        screen = trmnl.render(view:, device:, now:, mocks: many, variables:, custom_fields:)
        expect(screen).to have_no_problems.and(have_no_overlapping_text)
      end
    end
  end
end
