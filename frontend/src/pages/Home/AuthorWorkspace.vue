<template>
	<section
		class="author-workspace mt-8 rounded-2xl border border-outline-gray-2 bg-surface-base p-5 md:p-7"
	>
		<div class="author-hero" aria-labelledby="author-hero-title">
			<div class="author-hero-content">
				<span class="author-hero-eyebrow"
					>OVER U · LIFELONG ENERGY · BUSINESS HAPPINESS</span
				>
				<h1 id="author-hero-title">Студия курсов</h1>
				<p>
					Здесь вы создаёте программу обучения: курсы, модули, уроки, задания и
					тесты. Новые материалы сначала сохраняются как черновики.
				</p>
				<div class="author-hero-actions">
					<router-link :to="{ name: 'NewCourse' }" class="author-hero-create">
						<span class="lucide-plus size-4" /> Создать курс
					</router-link>
					<a href="/school" class="author-hero-secondary"
						>В школу OVER U <span class="lucide-arrow-up-right size-4"
					/></a>
				</div>
			</div>
			<div class="author-hero-art" aria-hidden="true">
				<img
					:src="'/assets/over_u/school/assets/brand-hero.jpg'"
					alt=""
					width="900"
					height="600"
					loading="lazy"
				/>
				<div class="author-hero-note">
					Знания, которые становятся действиями
				</div>
			</div>
		</div>
		<div
			class="flex flex-col gap-5 md:flex-row md:items-start md:justify-between"
		>
			<div class="max-w-2xl">
				<div
					class="studio-eyebrow mb-2 flex items-center gap-2 text-p-xs font-semibold uppercase tracking-[0.12em]"
				>
					<span class="lucide-pen-line size-4" />
					{{ __('OVER U · Студия курсов') }}
				</div>
				<h2 class="mb-2 text-2xl font-semibold text-ink-gray-9 md:text-3xl">
					{{ __('Мои учебные программы') }}
				</h2>
				<p class="m-0 text-p-base leading-6 text-ink-gray-6">
					{{
						__(
							'Create a course, arrange its chapters and lessons, and prepare learning materials in Frappe Learning.'
						)
					}}
				</p>
			</div>
			<div class="flex flex-wrap gap-2">
				<router-link :to="{ name: 'NewCourse' }" class="author-primary">
					<span class="lucide-plus size-4" />
					{{ __('Create course') }}
				</router-link>
				<router-link
					:to="{ name: 'Courses', query: { tab: 'created' } }"
					class="author-secondary"
				>
					{{ __('All my courses') }}
					<span class="lucide-arrow-up-right size-4" />
				</router-link>
			</div>
		</div>

		<div class="mt-6 grid grid-cols-1 gap-3 sm:grid-cols-3">
			<div class="author-stat">
				<span>{{ __('My courses') }}</span>
				<strong>{{ totalCount ?? '...' }}</strong>
			</div>
			<div class="author-stat">
				<span>{{ __('Not published') }}</span>
				<strong>{{ draftCount ?? '...' }}</strong>
			</div>
			<div class="author-stat">
				<span>{{ __('Published') }}</span>
				<strong>{{ publishedCount ?? '...' }}</strong>
			</div>
		</div>

		<div class="mt-7">
			<div class="mb-3 flex items-center justify-between gap-3">
				<h3 class="m-0 text-lg font-semibold text-ink-gray-9">
					{{ __('Continue editing') }}
				</h3>
				<router-link
					:to="{ name: 'Courses', query: { tab: 'created' } }"
					class="author-text-link"
				>
					{{ __('See all') }}
				</router-link>
			</div>

			<div v-if="courses.loading && !courses.data?.length" class="author-empty">
				<LoadingIndicator class="size-5 text-ink-gray-5" />
			</div>
			<div
				v-else-if="courses.data?.length"
				class="grid grid-cols-1 gap-3 lg:grid-cols-2"
			>
				<article
					v-for="course in courses.data.slice(0, 6)"
					:key="course.name"
					class="author-course"
				>
					<div class="flex min-w-0 items-start gap-3">
						<div class="author-course-icon">
							<span class="lucide-book-open size-5" />
						</div>
						<div class="min-w-0 flex-1">
							<div class="flex flex-wrap items-center gap-2">
								<h4
									class="m-0 truncate text-base font-semibold text-ink-gray-9"
								>
									{{ course.title }}
								</h4>
								<span class="author-status" :class="courseStatusClass(course)">
									{{ courseStatusLabel(course) }}
								</span>
							</div>
							<p class="mb-0 mt-1 line-clamp-2 text-p-sm text-ink-gray-6">
								{{
									course.short_introduction ||
									__('Add a short course introduction in course settings.')
								}}
							</p>
							<div
								class="mt-3 flex flex-wrap gap-x-4 gap-y-1 text-p-xs text-ink-gray-5"
							>
								<span>{{ __('{0} lessons').format(course.lessons || 0) }}</span>
								<span>{{
									__('{0} learners').format(course.enrollments || 0)
								}}</span>
							</div>
							<p v-if="course.enrollments" class="author-course-warning">
								{{
									__(
										'Deleting a lesson also deletes learner progress for that lesson.'
									)
								}}
							</p>
						</div>
					</div>
					<div
						class="mt-4 flex flex-wrap gap-2 border-t border-outline-gray-1 pt-3"
					>
						<router-link
							:to="editorRoute(course.name)"
							class="author-course-action"
						>
							<span class="lucide-pencil size-4" />
							{{ __('Edit course') }}
						</router-link>
						<router-link
							:to="{
								name: 'CourseDetail',
								params: { courseName: course.name },
							}"
							class="author-course-action"
						>
							<span class="lucide-eye size-4" />
							{{ __('Open course') }}
						</router-link>
					</div>
				</article>
			</div>
			<div v-else class="author-empty">
				<div class="author-empty-icon">
					<span class="lucide-book-open-check size-6" />
				</div>
				<div>
					<h4 class="mb-1 mt-0 text-base font-semibold text-ink-gray-9">
						{{ __('Your course list is empty') }}
					</h4>
					<p class="m-0 text-p-sm text-ink-gray-6">
						{{
							__(
								'Create a draft course to begin preparing your content. It will not appear in the student catalog until it is published.'
							)
						}}
					</p>
				</div>
				<router-link
					:to="{ name: 'NewCourse' }"
					class="author-secondary shrink-0"
				>
					{{ __('Create course') }}
				</router-link>
			</div>
		</div>

		<div class="mt-6 rounded-xl bg-surface-gray-1 p-4 md:p-5">
			<h3 class="mb-3 mt-0 text-base font-semibold text-ink-gray-9">
				{{ __('How course authoring works') }}
			</h3>
			<div
				class="grid grid-cols-1 gap-3 text-p-sm text-ink-gray-6 md:grid-cols-3"
			>
				<p class="m-0">
					<strong class="text-ink-gray-8">1.</strong>
					{{ __('Create the course draft and add the instructors.') }}
				</p>
				<p class="m-0">
					<strong class="text-ink-gray-8">2.</strong>
					{{
						__(
							'Open the course editor to add chapters, lessons, text, media, quizzes, and assignments.'
						)
					}}
				</p>
				<p class="m-0">
					<strong class="text-ink-gray-8">3.</strong>
					{{
						__(
							'Use Student View to preview a lesson. Publishing is controlled by the course moderator.'
						)
					}}
				</p>
			</div>
		</div>
	</section>
</template>

<script setup lang="ts">
import { computed } from 'vue'
import { createListResource, createResource, LoadingIndicator } from 'frappe-ui'

const ownCoursesFilter = { created: 1 }
const courses = createListResource({
	doctype: 'LMS Course',
	url: 'lms.lms.utils.get_courses',
	filters: ownCoursesFilter,
	fields: [
		'name',
		'title',
		'short_introduction',
		'published',
		'status',
		'lessons',
		'enrollments',
	],
	pageLength: 120,
	auto: true,
})

function countResource(filters: Record<string, number>) {
	return createResource({
		url: 'lms.lms.utils.get_course_count',
		params: { filters: { ...ownCoursesFilter, ...filters } },
		auto: true,
	})
}

const total = countResource({})
const drafts = countResource({ published: 0 })
const published = countResource({ published: 1 })
const totalCount = computed(() => total.data ?? null)
const draftCount = computed(() => drafts.data ?? null)
const publishedCount = computed(() => published.data ?? null)

function courseStatusLabel(course: Record<string, any>) {
	if (course.published) return __('Published')
	if (course.status === 'Under Review') return __('Under review')
	return __('Draft')
}

function courseStatusClass(course: Record<string, any>) {
	if (course.published) return 'is-published'
	if (course.status === 'Under Review') return 'is-review'
	return 'is-draft'
}

function editorRoute(courseName: string) {
	return { name: 'CourseDetail', params: { courseName }, hash: '#editor' }
}
</script>

<style scoped>
.author-workspace {
	--ou-paper: #f6f4ee;
	--ou-surface: #fffefa;
	--ou-forest: #214d3c;
	--ou-orange: #e94e15;
	--ou-line: #deded4;
	background: var(--ou-paper);
	border-color: var(--ou-line);
	border-radius: 24px;
	color: #202722;
}
.author-hero {
	display: grid;
	grid-template-columns: minmax(0, 1fr) minmax(0, 0.92fr);
	min-height: 315px;
	overflow: hidden;
	background: var(--ou-surface);
	border-radius: 22px;
	border: 1px solid var(--ou-line);
	margin-bottom: 30px;
}
.author-hero-content {
	padding: clamp(24px, 4vw, 48px);
	display: flex;
	flex-direction: column;
	align-items: flex-start;
	justify-content: center;
	gap: 16px;
	min-width: 0;
}
.author-hero-eyebrow {
	display: block;
	font-size: 10px;
	letter-spacing: 0.14em;
	font-weight: 750;
	color: var(--ou-orange);
	text-transform: uppercase;
}
.author-hero h1 {
	font: 400 clamp(35px, 4vw, 56px) / 1.05 Georgia, serif;
	letter-spacing: -0.035em;
	margin: 0;
	color: #202722;
}
.author-hero p {
	color: #68736b;
	font-size: 14px;
	line-height: 1.7;
	max-width: 52ch;
	margin: 0;
}
.author-hero-actions {
	display: flex;
	align-items: center;
	gap: 10px;
	flex-wrap: wrap;
	margin-top: 5px;
}
.author-hero-create,
.author-hero-secondary {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 9px;
	min-height: 43px;
	border-radius: 999px;
	padding: 10px 16px;
	font-weight: 700;
	text-decoration: none;
	font-size: 12px;
}
.author-hero-create {
	background: var(--ou-orange);
	color: white;
}
.author-hero-create:hover {
	background: #cb4212;
	color: white;
}
.author-hero-secondary {
	border: 1px solid var(--ou-line);
	color: var(--ou-forest);
	background: white;
}
.author-hero-secondary:hover {
	border-color: var(--ou-forest);
}
.author-hero-art {
	min-height: 315px;
	position: relative;
	overflow: hidden;
	background: #c8d0c0;
}
.author-hero-art img {
	width: 100%;
	height: 100%;
	position: absolute;
	inset: 0;
	display: block;
	object-fit: cover;
	object-position: 58% 50%;
}
.author-hero-note {
	position: absolute;
	right: 17px;
	bottom: 18px;
	background: rgba(255, 254, 250, 0.94);
	border-radius: 12px;
	color: #214d3c;
	font: 400 13px/1.3 Georgia, serif;
	padding: 12px 15px;
	box-shadow: 0 8px 20px #172f242a;
}
.author-stat {
	border-color: var(--ou-line) !important;
	background: var(--ou-surface) !important;
}
.author-stat strong {
	color: var(--ou-forest) !important;
}
.author-course {
	border-color: var(--ou-line) !important;
	background: var(--ou-surface) !important;
}
.author-primary {
	background: var(--ou-orange) !important;
	border-radius: 999px !important;
}
.author-secondary,
.author-course-action {
	border-radius: 999px !important;
}
.author-text-link {
	color: var(--ou-forest) !important;
}
@media (max-width: 800px) {
	.author-hero {
		grid-template-columns: 1fr;
	}
	.author-hero-art {
		min-height: 215px;
	}
}
@media (max-width: 640px) {
	.author-workspace {
		padding: 14px !important;
		border-radius: 18px;
	}
	.author-hero-content {
		padding: 24px 20px;
	}
	.author-hero h1 {
		font-size: 41px;
	}
	.author-hero-art {
		min-height: 180px;
	}
}
.studio-eyebrow {
	color: #d94a20;
}
.author-primary,
.author-secondary,
.author-course-action {
	display: inline-flex;
	align-items: center;
	justify-content: center;
	gap: 0.5rem;
	min-height: 2.5rem;
	border-radius: 0.65rem;
	padding: 0.6rem 0.9rem;
	font-size: 0.875rem;
	font-weight: 600;
	text-decoration: none;
}
.author-primary {
	background: #e94f24;
	color: white;
}
.author-primary:hover {
	background: #cf3f18;
	color: white;
}
.author-secondary {
	border: 1px solid #d8ddd7;
	background: white;
	color: #35433a;
}
.author-secondary:hover,
.author-course-action:hover {
	border-color: #e94f24;
	color: #bd3c1a;
}
.author-stat {
	display: flex;
	min-height: 5rem;
	flex-direction: column;
	justify-content: space-between;
	border: 1px solid #e7e9e4;
	border-radius: 0.85rem;
	background: white;
	padding: 0.9rem 1rem;
}
.author-stat span {
	color: #6b746d;
	font-size: 0.8rem;
}
.author-stat strong {
	color: #263d31;
	font-size: 1.55rem;
	line-height: 1;
}
.author-course {
	min-width: 0;
	border: 1px solid #e7e9e4;
	border-radius: 0.9rem;
	background: white;
	padding: 1rem;
}
.author-course-icon,
.author-empty-icon {
	display: grid;
	flex: none;
	place-items: center;
	width: 2.6rem;
	height: 2.6rem;
	border-radius: 0.8rem;
	background: #fff0e9;
	color: #e94f24;
}
.author-status {
	border-radius: 999px;
	padding: 0.18rem 0.55rem;
	font-size: 0.7rem;
	font-weight: 600;
}
.author-status.is-published {
	background: #e8f2eb;
	color: #286043;
}
.author-status.is-draft {
	background: #fff0e9;
	color: #aa391b;
}
.author-status.is-review {
	background: #fff4d9;
	color: #805c12;
}
.author-course-warning {
	margin: 0.6rem 0 0;
	border-left: 2px solid #db9a26;
	padding-left: 0.6rem;
	color: #805c12;
	font-size: 0.75rem;
	line-height: 1.4;
}
.author-course-action {
	min-height: 2rem;
	border: 1px solid transparent;
	padding: 0.3rem 0.55rem;
	color: #445148;
	font-size: 0.8rem;
}
.author-empty {
	display: flex;
	min-height: 7rem;
	align-items: center;
	gap: 1rem;
	border: 1px dashed #d4dbd4;
	border-radius: 0.9rem;
	background: #fff;
	padding: 1.25rem;
}
.author-text-link {
	color: #a83c20;
	font-size: 0.85rem;
	font-weight: 600;
	text-decoration: none;
}
.author-text-link:hover {
	text-decoration: underline;
}
@media (max-width: 640px) {
	.author-empty {
		flex-wrap: wrap;
	}
	.author-empty .author-secondary {
		width: 100%;
	}
}
</style>
