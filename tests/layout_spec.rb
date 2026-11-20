# frozen_string_literal: true

require_relative 'support/layout_checks'

# Data that stretches the layout, drawn in every view on TRMNL OG and TRMNL X, landscape and portrait.
# The checks are in tests/support/layout_checks.rb; the clock and Vikunja are the ones in plugin_spec.rb.
RSpec.describe 'Vikunja Tasks layout' do
  def fixture(name) = JSON.parse(File.read(File.join(__dir__, 'fixtures', name)))

  OPEN_TASKS = 'https://tasks.example.com/api/v1/tasks?*filter=done+%3D+false*'
  DONE_TASKS = 'https://tasks.example.com/api/v1/tasks?*filter=done+%3D+true*'
  PROJECTS = 'https://tasks.example.com/api/v1/projects*'

  let(:now) { Time.utc(2026, 11, 11, 10) }
  let(:variables) { { 'trmnl' => { 'user' => { 'time_zone_iana' => 'Europe/Berlin', 'locale' => 'en' } } } }
  let(:custom_fields) { { 'base_url' => 'https://tasks.example.com', 'api_token' => 'tk_test', 'language' => 'en' } }
  let(:projects) { fixture('projects.json') + [{ 'id' => 6, 'title' => 'Renovating the summer house by the lake' }] }

  def answering(open, done) = { OPEN_TASKS => { json: open }, DONE_TASKS => { json: done }, PROJECTS => { json: projects } }

  # Titles that wrap, a word too long for any line, many labels and people, a long project name, a long done task.
  def long_text = { now:, variables:, custom_fields:, mocks: answering(fixture('long-text.json'), fixture('long-text-done.json')) }
  # The same in German, whose words are longer.
  def long_text_de = long_text.merge(custom_fields: custom_fields.merge('language' => 'de'))
  # More tasks than any view holds.
  def many = { now:, variables:, custom_fields:, mocks: answering(fixture('many-tasks.json'), fixture('done-today.json')) }
  # Nothing open, nothing done.
  def nothing = { now:, variables:, custom_fields:, mocks: answering([], []) }

  it_behaves_like 'a layout that holds up',
                  'long titles' => :long_text, 'long German titles' => :long_text_de,
                  'more tasks than fit' => :many, 'an empty list' => :nothing
end
